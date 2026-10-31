import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from .models import Memory, Source, Company, Project, Person
from .schemas import (
    MemoryCreate,
    MemoryUpdate,
    MemoryResponse,
    CompanyCreate,
    CompanyResponse,
    ProjectCreate,
    ProjectResponse,
    PersonCreate,
    PersonResponse,
    SourceCreate,
    SourceResponse,
    MemoryHistoryResponse
)
from .embedding_service import embedding_service
from .relationship_service import relationship_service

logger = logging.getLogger("memory_engine.memory_service")


class MemoryService:
    """
    High-level orchestrator for business memory persistence, source traceability,
    and entity relationships in AFTERMIND.
    """

    # -------------------------------------------------------------
    # Company, Project, Person & Source Management
    # -------------------------------------------------------------
    def get_or_create_company(self, db: Session, req: CompanyCreate) -> Company:
        company = db.query(Company).filter(Company.name == req.name).first()
        if not company:
            company = Company(name=req.name, domain=req.domain)
            db.add(company)
            db.commit()
            db.refresh(company)
        return company

    def get_or_create_project(self, db: Session, req: ProjectCreate) -> Project:
        project = db.query(Project).filter(
            Project.name == req.name,
            Project.company_id == req.company_id
        ).first()
        if not project:
            project = Project(
                company_id=req.company_id,
                name=req.name,
                description=req.description,
                status=req.status or "active"
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        return project

    def get_or_create_person(self, db: Session, req: PersonCreate) -> Person:
        person = db.query(Person).filter(
            Person.name == req.name,
            Person.company_id == req.company_id
        ).first()
        if not person:
            person = Person(
                company_id=req.company_id,
                name=req.name,
                email=req.email,
                role=req.role
            )
            db.add(person)
            db.commit()
            db.refresh(person)
        return person

    def create_source(self, db: Session, req: SourceCreate) -> Source:
        # Validate company exists
        company = db.query(Company).filter(Company.id == req.company_id).first()
        if not company:
            raise ValueError(f"Company {req.company_id} does not exist.")

        source = Source(
            company_id=req.company_id,
            project_id=req.project_id,
            author_id=req.author_id,
            title=req.title,
            source_type=req.source_type.value,
            raw_content=req.raw_content,
            source_url=req.source_url,
            meta_info=req.meta_info
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    # -------------------------------------------------------------
    # Memory CRUD & Business Logic
    # -------------------------------------------------------------
    def create_memory(self, db: Session, req: MemoryCreate) -> MemoryResponse:
        """
        Ingest a structured memory item (decision, requirement, commitment, deadline).
        Generates vector embedding, stores source reference, and links decision history.
        """
        # Validate source reference
        source = db.query(Source).filter(
            Source.id == req.source_id,
            Source.company_id == req.company_id
        ).first()
        if not source:
            raise ValueError(f"Source with id {req.source_id} not found for company {req.company_id}")

        # If project_id not provided, inherit from source if available
        project_id = req.project_id or source.project_id

        # Generate vector embedding for semantic search
        text_to_embed = f"{req.title}: {req.content}"
        if req.tags:
            text_to_embed += f" [Tags: {', '.join(req.tags)}]"
        embedding_vec = embedding_service.generate_embedding(text_to_embed)

        memory = Memory(
            company_id=req.company_id,
            project_id=project_id,
            source_id=req.source_id,
            author_id=req.author_id,
            memory_type=req.memory_type.value,
            title=req.title,
            content=req.content,
            status=req.status.value if req.status else "active",
            confidence=req.confidence,
            previous_memory_id=req.previous_memory_id,
            change_reason=req.change_reason,
            tags=req.tags or [],
            meta_info=req.meta_info or {},
            embedding=embedding_vec
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)

        # Handle decision history / superseding relationship
        if req.previous_memory_id:
            relationship_service.link_superseded_memory(
                db=db,
                new_memory=memory,
                previous_memory_id=req.previous_memory_id,
                change_reason=req.change_reason
            )

        return self._format_memory_response(memory)

    def get_memory(self, db: Session, memory_id: str, company_id: Optional[str] = None) -> Optional[MemoryResponse]:
        """Retrieve memory by ID with optional tenant isolation verification."""
        query = db.query(Memory).filter(Memory.id == memory_id)
        if company_id:
            query = query.filter(Memory.company_id == company_id)
        memory = query.first()
        if not memory:
            return None
        return self._format_memory_response(memory)

    def list_memories(
        self,
        db: Session,
        company_id: str,
        project_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[MemoryResponse]:
        """List memories for a company with metadata filtering."""
        query = db.query(Memory).filter(Memory.company_id == company_id)

        if project_id:
            query = query.filter(Memory.project_id == project_id)
        if memory_type:
            query = query.filter(Memory.memory_type == memory_type)
        if status:
            query = query.filter(Memory.status == status)

        query = query.order_by(Memory.created_at.desc()).offset(skip).limit(limit)
        return [self._format_memory_response(m) for m in query.all()]

    def get_company_memories(self, db: Session, company_id: str) -> List[MemoryResponse]:
        """Fetch all memories belonging to a company."""
        return self.list_memories(db=db, company_id=company_id, limit=200)

    def get_project_memories(self, db: Session, project_id: str, company_id: Optional[str] = None) -> List[MemoryResponse]:
        """Fetch all memories associated with a project."""
        query = db.query(Memory).filter(Memory.project_id == project_id)
        if company_id:
            query = query.filter(Memory.company_id == company_id)
        return [self._format_memory_response(m) for m in query.order_by(Memory.created_at.desc()).all()]

    def get_memory_history(self, db: Session, memory_id: str) -> Optional[MemoryHistoryResponse]:
        """Retrieve the decision evolution and timeline of changes for a memory."""
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            return None

        timeline_entities = relationship_service.get_memory_timeline(db, memory_id)
        timeline_responses = [self._format_memory_response(m) for m in timeline_entities]
        relationships = relationship_service.get_memory_relationships(db, memory_id)

        return MemoryHistoryResponse(
            memory_id=memory.id,
            company_id=memory.company_id,
            current_status=memory.status,
            timeline=timeline_responses,
            relationships=relationships
        )

    def _format_memory_response(self, memory: Memory) -> MemoryResponse:
        """Helper to serialize Memory model to MemoryResponse with relations."""
        source_title = memory.source.title if memory.source else None
        source_type = memory.source.source_type if memory.source else None
        project_name = memory.project.name if memory.project else None
        company_name = memory.company.name if memory.company else None

        return MemoryResponse(
            id=memory.id,
            company_id=memory.company_id,
            project_id=memory.project_id,
            source_id=memory.source_id,
            author_id=memory.author_id,
            memory_type=memory.memory_type,
            title=memory.title,
            content=memory.content,
            status=memory.status,
            confidence=memory.confidence,
            previous_memory_id=memory.previous_memory_id,
            change_reason=memory.change_reason,
            tags=memory.tags or [],
            meta_info=memory.meta_info or {},
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            source_title=source_title,
            source_type=source_type,
            project_name=project_name,
            company_name=company_name
        )


memory_service = MemoryService()
