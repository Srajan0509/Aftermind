"""FastAPI endpoints for Module 2: Intelligent Memory Extraction."""
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import ValidationError

from .config import settings
from .extractor import ExtractionError, memory_extractor
from .schemas import ExtractionRequest, ExtractionResponse
from memory_engine.database import get_db
from memory_engine.memory_service import memory_service
from memory_engine.schemas import (
    SourceCreate,
    MemoryCreate,
    SourceType,
    MemoryType as Mod3MemoryType,
    MemoryStatus,
)

router = APIRouter(
    prefix="/api/extraction",
    tags=["Module 2: Intelligent Memory Extraction"],
)


@router.post("/extract", response_model=ExtractionResponse)
def extract_business_memories(request: ExtractionRequest):
    """Extract structured business memories from standardized source text."""
    text = request.extracted_text or request.text or ""
    if len(text) > settings.max_input_characters:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Input exceeds the maximum of {settings.max_input_characters} characters.",
        )
    try:
        return memory_extractor.extract(request)
    except ExtractionError as exc:
        message = str(exc)
        msg_lower = message.lower()
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "not configured" in msg_lower or "no llm api key" in msg_lower
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=code, detail=message) from exc


@router.post("/extract-and-store")
def extract_and_store_business_memories(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Extracts structured memories from text and persists them into Module 3 Long-Term Memory.
    Returns stored memory count, created memory IDs, and extraction preview.
    """
    text = payload.get("text") or payload.get("extracted_text") or ""
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Input text cannot be blank.")

    company_id = payload.get("company_id") or "default-org"
    source_title = payload.get("source_title") or payload.get("title") or "Executive Discussion"

    # 1. Run memory extraction via Module 2
    ext_req = ExtractionRequest(
        company_id=company_id,
        extracted_text=text,
        title=source_title
    )
    try:
        extraction_result = memory_extractor.extract(ext_req)
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    # 2. Register Source in Module 3
    summary_text = getattr(extraction_result, "source_summary", None)
    if not summary_text:
        summary_text = f"Extracted {len(extraction_result.memories)} business memories from source."

    try:
        source_create = SourceCreate(
            company_id=company_id,
            title=source_title,
            source_type=SourceType.DOCUMENT,
            raw_content=text,
            meta_info={"summary": summary_text}
        )
        source = memory_service.create_source(db, source_create)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create source: {exc}")

    # 3. Store individual memories with vector embeddings
    type_map = {
        "decision": Mod3MemoryType.DECISION,
        "client_requirement": Mod3MemoryType.CLIENT_REQUIREMENT,
        "employee_commitment": Mod3MemoryType.EMPLOYEE_COMMITMENT,
        "important_deadline": Mod3MemoryType.IMPORTANT_DEADLINE,
        "meeting_discussion": Mod3MemoryType.MEETING_DISCUSSION,
        "general_info": Mod3MemoryType.GENERAL_INFO,
    }

    stored_ids = []
    for mem in extraction_result.memories:
        m_type_val = mem.memory_type.value if hasattr(mem.memory_type, "value") else str(mem.memory_type)
        mod3_type = type_map.get(m_type_val.lower(), Mod3MemoryType.GENERAL_INFO)

        tags = list(mem.tags or [])
        meta = dict(mem.meta_info or {})
        if mem.person:
            meta["assignee"] = mem.person
        if mem.confidence:
            meta["extraction_confidence"] = mem.confidence

        try:
            mem_create = MemoryCreate(
                company_id=company_id,
                source_id=source.id,
                memory_type=mod3_type,
                title=mem.title,
                content=mem.content,
                confidence=mem.confidence if mem.confidence is not None else 0.95,
                status=MemoryStatus.ACTIVE,
                tags=tags,
                meta_info=meta
            )
            created_mem = memory_service.create_memory(db, mem_create)
            stored_ids.append(created_mem.id)
        except Exception as exc:
            # Continue saving remaining memories if one fails
            continue

    return {
        "status": "success",
        "stored_count": len(stored_ids),
        "source_id": source.id,
        "memory_ids": stored_ids,
        "source_summary": summary_text,
        "extraction_summary": summary_text or f"Extracted and indexed {len(stored_ids)} memories.",
        "memories": [m.model_dump() for m in extraction_result.memories],
        "entities": [e.model_dump() for e in extraction_result.entities]
    }


@router.get("/health")
def extraction_health():
    """Report module configuration without exposing credentials."""
    configured = False
    if settings.llm_provider == "openai":
        configured = bool(settings.openai_api_key)
    elif settings.llm_provider == "gemini":
        configured = bool(settings.gemini_api_key)
    elif settings.llm_provider == "groq":
        configured = bool(settings.groq_api_key)
    elif settings.llm_provider == "openrouter":
        configured = bool(settings.openrouter_api_key)

    return {
        "status": "healthy",
        "module": "Module 2: Intelligent Memory Extraction",
        "provider": settings.llm_provider,
        "provider_configured": configured,
    }
