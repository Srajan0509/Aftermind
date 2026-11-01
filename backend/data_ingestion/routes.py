import json
import logging
from typing import Optional, Any
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

# Optional DB dependency injection
try:
    from memory_engine.database import get_db
except ImportError:
    def get_db():
        yield None

from .config import ingestion_settings
from .normalizer import TextNormalizationError
from .parsers.base import DocumentParsingError
from .transcribers.base import AudioTranscriptionError
from .schemas import (
    TextIngestRequest,
    IngestionResponse,
    IngestionHealthResponse,
    IngestionSourceType,
)
from .service import ingestion_service

logger = logging.getLogger("data_ingestion.routes")

router = APIRouter(
    prefix="/api/ingest",
    tags=["Module 1: Multi-Source AI Data Ingestion"],
)


def _clean_form_str(val: Any) -> Optional[str]:
    """Extracts string value if passed, or None if omitted or default Form object."""
    if val is None or not isinstance(val, str):
        return None
    cleaned = val.strip()
    return cleaned if cleaned else None


def _read_upload_file_bytes(file: UploadFile) -> bytes:
    """Safely extracts bytes from an UploadFile supporting both spooled and memory buffers."""
    try:
        if hasattr(file, "file") and hasattr(file.file, "read"):
            data = file.file.read()
            if isinstance(data, bytes):
                return data
        if hasattr(file, "read"):
            data = file.read()
            if isinstance(data, bytes):
                return data
        return b""
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read uploaded file: {e}")


@router.post("/text", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_text_endpoint(
    request: TextIngestRequest,
    db: Optional[Session] = Depends(get_db)
):
    """
    Ingest raw text, meeting transcript, or chat message directly.
    Standardizes text, optionally persists source in Module 3, and optionally runs Module 2 extraction.
    """
    try:
        return ingestion_service.ingest_text(request, db=db)
    except TextNormalizationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Text ingestion error: {e}")


@router.post("/document", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_document_endpoint(
    file: UploadFile = File(...),
    company_id: Optional[str] = Form(None, description="Target company UUID (optional for standalone parsing)"),
    title: Optional[str] = Form(None, description="Optional title for the document source"),
    project_id: Optional[str] = Form(None, description="Optional project UUID"),
    author_id: Optional[str] = Form(None, description="Optional author UUID"),
    source_type: IngestionSourceType = Form(IngestionSourceType.DOCUMENT),
    trigger_extraction: bool = Form(True, description="Forward extracted text to Module 2 if company_id provided"),
    metadata: Optional[str] = Form(None, description="Optional JSON string of extra metadata"),
    db: Optional[Session] = Depends(get_db)
):
    """
    Upload and ingest document files (PDF, DOCX, TXT).
    Parses content with PyMuPDF/XML ElementTree, validates MIME and integrity, and routes to Module 2/3.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file or filename.")

    content = _read_upload_file_bytes(file)

    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded file is empty (0 bytes).")

    # Clean default Form values
    c_id = _clean_form_str(company_id)
    t_val = _clean_form_str(title)
    p_id = _clean_form_str(project_id)
    a_id = _clean_form_str(author_id)
    m_val = _clean_form_str(metadata)
    st_val = source_type if isinstance(source_type, IngestionSourceType) else IngestionSourceType.DOCUMENT
    ext_trig = trigger_extraction if isinstance(trigger_extraction, bool) else True

    extra_meta = {}
    if m_val:
        try:
            extra_meta = json.loads(m_val)
        except Exception:
            extra_meta = {"raw_metadata": m_val}

    try:
        return ingestion_service.ingest_document(
            content=content,
            filename=file.filename,
            company_id=c_id,
            db=db,
            title=t_val,
            project_id=p_id,
            author_id=a_id,
            source_type=st_val,
            trigger_extraction=ext_trig,
            extra_metadata=extra_meta
        )
    except DocumentParsingError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Document ingestion error: {e}")


@router.post("/audio", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_audio_endpoint(
    file: UploadFile = File(...),
    company_id: Optional[str] = Form(None, description="Target company UUID (optional for standalone parsing)"),
    title: Optional[str] = Form(None, description="Optional title for the audio source"),
    project_id: Optional[str] = Form(None, description="Optional project UUID"),
    author_id: Optional[str] = Form(None, description="Optional author UUID"),
    language: Optional[str] = Form(None, description="Optional language ISO code, e.g. 'en'"),
    source_type: IngestionSourceType = Form(IngestionSourceType.VOICE_NOTE),
    trigger_extraction: bool = Form(True, description="Forward transcript to Module 2 if company_id provided"),
    metadata: Optional[str] = Form(None, description="Optional JSON string of extra metadata"),
    db: Optional[Session] = Depends(get_db)
):
    """
    Upload and ingest audio recordings or voice notes (MP3, WAV, M4A).
    Transcribes audio via OpenAI Whisper or Google Gemini, validates MIME, and routes to Module 2/3.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file or filename.")

    content = _read_upload_file_bytes(file)

    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded audio file is empty (0 bytes).")

    # Clean default Form values
    c_id = _clean_form_str(company_id)
    t_val = _clean_form_str(title)
    p_id = _clean_form_str(project_id)
    a_id = _clean_form_str(author_id)
    l_val = _clean_form_str(language)
    m_val = _clean_form_str(metadata)
    st_val = source_type if isinstance(source_type, IngestionSourceType) else IngestionSourceType.VOICE_NOTE
    ext_trig = trigger_extraction if isinstance(trigger_extraction, bool) else True

    extra_meta = {}
    if m_val:
        try:
            extra_meta = json.loads(m_val)
        except Exception:
            extra_meta = {"raw_metadata": m_val}

    try:
        return ingestion_service.ingest_audio(
            audio_bytes=content,
            filename=file.filename,
            company_id=c_id,
            db=db,
            title=t_val,
            project_id=p_id,
            author_id=a_id,
            language=l_val,
            source_type=st_val,
            trigger_extraction=ext_trig,
            extra_metadata=extra_meta
        )
    except AudioTranscriptionError as e:
        msg = str(e)
        if "unavailable" in msg.lower() or "not configured" in msg.lower():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=msg)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Audio ingestion error: {e}")


@router.post("/pipeline", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_pipeline_endpoint(
    request: TextIngestRequest,
    db: Optional[Session] = Depends(get_db)
):
    """
    Unified end-to-end ingestion pipeline:
    Receives text/transcript -> Persists in Module 3 (if db available) -> Dispatches to Module 2.
    """
    return ingest_text_endpoint(request, db=db)


@router.get("/health", response_model=IngestionHealthResponse)
def ingestion_health_endpoint():
    """Health check reporting configuration and supported formats for Module 1."""
    return IngestionHealthResponse(
        status="healthy",
        module="Module 1: Multi-Source AI Data Ingestion",
        supported_document_types=sorted(list(ingestion_settings.SUPPORTED_DOCUMENT_EXTENSIONS)),
        supported_audio_types=sorted(list(ingestion_settings.SUPPORTED_AUDIO_EXTENSIONS)),
        transcriber_provider=ingestion_settings.AUDIO_TRANSCRIBER_PROVIDER,
        max_document_size_mb=ingestion_settings.MAX_DOCUMENT_SIZE_BYTES / (1024 * 1024),
        max_audio_size_mb=ingestion_settings.MAX_AUDIO_SIZE_BYTES / (1024 * 1024),
        max_input_characters=ingestion_settings.MAX_TEXT_CHARACTERS
    )
