from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .database import get_db
from .schemas import (
    MemoryCreate,
    MemoryResponse,
    CompanyCreate,
    CompanyResponse,
    ProjectCreate,
    ProjectResponse,
    PersonCreate,
    PersonResponse,
    SourceCreate,
    SourceResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    RAGChatRequest,
    RAGChatResponse,
    MemoryRelationshipCreate,
    MemoryRelationshipResponse,
    MemoryHistoryResponse
)
from .memory_service import memory_service
from .relationship_service import relationship_service
from .vector_search import vector_search_engine
from .rag_engine import rag_engine

router = APIRouter(prefix="/api", tags=["Module 3: Connected Long-Term Memory & Semantic Search"])


# -------------------------------------------------------------
# Entity Management (Companies, Projects, People, Sources)
# -------------------------------------------------------------
@router.post("/companies/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(req: CompanyCreate, db: Session = Depends(get_db)):
    """Register a new client company / tenant organization."""
    company = memory_service.get_or_create_company(db, req)
    return CompanyResponse.model_validate(company)


@router.post("/projects/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(req: ProjectCreate, db: Session = Depends(get_db)):
    """Register a project under a company."""
    project = memory_service.get_or_create_project(db, req)
    return ProjectResponse.model_validate(project)


@router.post("/people/", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_person(req: PersonCreate, db: Session = Depends(get_db)):
    """Register an employee, stakeholder or client contact."""
    person = memory_service.get_or_create_person(db, req)
    return PersonResponse.model_validate(person)


@router.post("/sources/", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(req: SourceCreate, db: Session = Depends(get_db)):
    """Register an original source (meeting transcript, document, voice note)."""
    try:
        source = memory_service.create_source(db, req)
        return SourceResponse.model_validate(source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------
# Memory Endpoints
# -------------------------------------------------------------
@router.post("/memories/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_memory(req: MemoryCreate, db: Session = Depends(get_db)):
    """
    Store an extracted business memory item with vector embedding and source reference.
    Accepts structured output from Dhanesh's extraction module.
    """
    try:
        return memory_service.create_memory(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/memories/", response_model=List[MemoryResponse])
def list_memories(
    company_id: str = Query(..., description="Company ID required to enforce tenant isolation"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    memory_type: Optional[str] = Query(None, description="Filter by memory classification"),
    status: Optional[str] = Query(None, description="Filter by memory status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve memories scoped to a company with optional filters."""
    return memory_service.list_memories(
        db=db,
        company_id=company_id,
        project_id=project_id,
        memory_type=memory_type,
        status=status,
        skip=skip,
        limit=limit
    )


@router.get("/memories/{memory_id}", response_model=MemoryResponse)
def get_memory(
    memory_id: str,
    company_id: Optional[str] = Query(None, description="Optional tenant verification"),
    db: Session = Depends(get_db)
):
    """Retrieve a single memory with complete source reference."""
    mem = memory_service.get_memory(db, memory_id=memory_id, company_id=company_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return mem


@router.get("/memories/{memory_id}/history", response_model=MemoryHistoryResponse)
def get_memory_history(memory_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the chronological decision evolution and timeline of changes for a memory.
    Traces when decisions were revised across multiple meetings.
    """
    history = memory_service.get_memory_history(db, memory_id=memory_id)
    if not history:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return history


@router.get("/companies/{company_id}/memories", response_model=List[MemoryResponse])
def get_company_memories(company_id: str, db: Session = Depends(get_db)):
    """Fetch all memories belonging to a company."""
    return memory_service.get_company_memories(db, company_id=company_id)


@router.get("/projects/{project_id}/memories", response_model=List[MemoryResponse])
def get_project_memories(
    project_id: str,
    company_id: Optional[str] = Query(None, description="Optional tenant validation"),
    db: Session = Depends(get_db)
):
    """Fetch all memories for a project."""
    return memory_service.get_project_memories(db, project_id=project_id, company_id=company_id)


# -------------------------------------------------------------
# Semantic Search & RAG
# -------------------------------------------------------------
@router.post("/search/", response_model=SemanticSearchResponse)
def semantic_search(req: SemanticSearchRequest, db: Session = Depends(get_db)):
    """
    Natural language semantic search over business memories using vector similarity and metadata filtering.
    Mandatory company_id guarantees data isolation.
    """
    results = vector_search_engine.search(
        db=db,
        query=req.query,
        company_id=req.company_id,
        project_id=req.project_id,
        memory_type=req.memory_type.value if req.memory_type else None,
        status=req.status.value if req.status else None,
        limit=req.limit,
        min_similarity=req.min_similarity
    )
    return SemanticSearchResponse(
        query=req.query,
        company_id=req.company_id,
        results_count=len(results),
        results=results
    )


@router.post("/chat/", response_model=RAGChatResponse)
def rag_chat(req: RAGChatRequest, db: Session = Depends(get_db)):
    """
    RAG Pipeline: Answers employee questions using retrieved business memories.
    Always includes cited source references.
    """
    return rag_engine.answer_question(db=db, req=req)


# -------------------------------------------------------------
# Memory Relationships
# -------------------------------------------------------------
@router.post("/relationships/", response_model=MemoryRelationshipResponse, status_code=status.HTTP_201_CREATED)
def create_relationship(req: MemoryRelationshipCreate, db: Session = Depends(get_db)):
    """Create an explicit directed relationship between two memories (supersedes, updates, relates_to)."""
    try:
        return relationship_service.create_relationship(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
