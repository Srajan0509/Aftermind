import json
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from memory_engine.database import get_db
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

router = APIRouter(
    prefix="/api/ingest",
    tags=["Module 1: Multi-Source AI Data Ingestion"],
)


@router.post("/text", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_text_endpoint(
    request: TextIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Ingest raw text, meeting transcript, or chat message directly.
    Standardizes text, registers source in Module 3, and optionally runs Module 2 extraction.
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
async def ingest_document_endpoint(
    file: UploadFile = File(...),
    company_id: str = Form(..., description="Target company UUID"),
    title: Optional[str] = Form(None, description="Optional title for the document source"),
    project_id: Optional[str] = Form(None, description="Optional project UUID"),
    author_id: Optional[str] = Form(None, description="Optional author UUID"),
    source_type: IngestionSourceType = Form(IngestionSourceType.DOCUMENT),
    trigger_extraction: bool = Form(True, description="Forward extracted text to Module 2"),
    metadata: Optional[str] = Form(None, description="Optional JSON string of extra metadata"),
    db: Session = Depends(get_db)
):
    """
    Upload and ingest document files (.txt, .md, .pdf, .docx, .csv, .json).
    Parses content, normalizes text, registers source in Module 3, and triggers Module 2 extraction.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file name.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded file is empty (0 bytes).")

    extra_meta = {}
    if metadata:
        try:
            extra_meta = json.loads(metadata)
        except Exception:
            extra_meta = {"raw_metadata": metadata}

    try:
        return ingestion_service.ingest_document(
            content=content,
            filename=file.filename,
            company_id=company_id,
            db=db,
            title=title,
            project_id=project_id,
            author_id=author_id,
            source_type=source_type,
            trigger_extraction=trigger_extraction,
            extra_metadata=extra_meta
        )
    except DocumentParsingError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Document ingestion error: {e}")


@router.post("/audio", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_audio_endpoint(
    file: UploadFile = File(...),
    company_id: str = Form(..., description="Target company UUID"),
    title: Optional[str] = Form(None, description="Optional title for the audio source"),
    project_id: Optional[str] = Form(None, description="Optional project UUID"),
    author_id: Optional[str] = Form(None, description="Optional author UUID"),
    language: Optional[str] = Form(None, description="Optional language ISO code, e.g. 'en'"),
    source_type: IngestionSourceType = Form(IngestionSourceType.VOICE_NOTE),
    trigger_extraction: bool = Form(True, description="Forward transcript to Module 2"),
    metadata: Optional[str] = Form(None, description="Optional JSON string of extra metadata"),
    db: Session = Depends(get_db)
):
    """
    Upload and ingest audio recordings or voice notes (.mp3, .wav, .m4a, .ogg, .webm, .flac).
    Transcribes audio via Whisper/Gemini, standardizes text, registers in Module 3, and triggers Module 2.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing file name.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded audio file is empty (0 bytes).")

    extra_meta = {}
    if metadata:
        try:
            extra_meta = json.loads(metadata)
        except Exception:
            extra_meta = {"raw_metadata": metadata}

    try:
        return ingestion_service.ingest_audio(
            audio_bytes=content,
            filename=file.filename,
            company_id=company_id,
            db=db,
            title=title,
            project_id=project_id,
            author_id=author_id,
            language=language,
            source_type=source_type,
            trigger_extraction=trigger_extraction,
            extra_metadata=extra_meta
        )
    except AudioTranscriptionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Audio ingestion error: {e}")


@router.post("/pipeline", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_pipeline_endpoint(
    request: TextIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Unified end-to-end ingestion pipeline:
    Receives text/transcript -> Persists in Module 3 -> Dispatches to Module 2.
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
