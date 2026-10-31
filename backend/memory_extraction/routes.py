"""FastAPI endpoints for Module 2."""
from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from .config import settings
from .extractor import ExtractionError, memory_extractor
from .schemas import ExtractionRequest, ExtractionResponse

router = APIRouter(
    prefix="/api/extraction",
    tags=["Module 2: Intelligent Memory Extraction"],
)


@router.post("/extract", response_model=ExtractionResponse)
def extract_business_memories(request: ExtractionRequest):
    """Extract structured business memories from standardized source text."""
    if len(request.extracted_text) > settings.max_input_characters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Input exceeds the maximum of {settings.max_input_characters} characters.",
        )
    try:
        return memory_extractor.extract(request)
    except ExtractionError as exc:
        message = str(exc)
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "not configured" in message.lower()
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=code, detail=message) from exc


@router.get("/health")
def extraction_health():
    """Report module configuration without exposing credentials."""
    return {
        "status": "healthy",
        "module": "Module 2: Intelligent Memory Extraction",
        "provider": settings.llm_provider,
        "provider_configured": (
            bool(settings.openai_api_key) if settings.llm_provider == "openai"
            else bool(settings.gemini_api_key) if settings.llm_provider == "gemini"
            else False
        ),
    }
