import logging
import os
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from .config import ingestion_settings
from .normalizer import text_normalizer, TextNormalizationError
from .parsers.dispatcher import document_dispatcher
from .parsers.base import DocumentParsingError
from .transcribers.manager import audio_transcription_manager
from .transcribers.base import AudioTranscriptionError
from .schemas import (
    DocumentParseResult,
    AudioTranscribeResult,
    TextIngestRequest,
    IngestionResponse,
    IngestionSourceType,
)

# Optional Integration with Module 3 (Persistence)
try:
    from memory_engine.memory_service import memory_service
    from memory_engine.schemas import SourceCreate, SourceType as Mod3SourceType
    MODULE_3_AVAILABLE = True
except ImportError:
    MODULE_3_AVAILABLE = False
    memory_service = None

# Optional Integration with Module 2 (Extraction)
try:
    from memory_extraction.extractor import memory_extractor
    from memory_extraction.schemas import ExtractionRequest
    MODULE_2_AVAILABLE = True
except ImportError:
    MODULE_2_AVAILABLE = False
    memory_extractor = None

logger = logging.getLogger("data_ingestion.service")


class IngestionService:
    """
    Core orchestrator for Module 1: Multi-Source AI Data Ingestion.
    Standardizes inputs across documents (PDF, DOCX, TXT), audio recordings (MP3, WAV, M4A),
    and raw text transcripts.

    Design Rule: Module 1 is completely independently functional.
    Module 2 and Module 3 integrations are optional and never prevent basic ingestion from working.
    """

    def _map_source_type_to_mod3(self, source_type: IngestionSourceType):
        """Maps Module 1 source types to Module 3 enum when available."""
        if not MODULE_3_AVAILABLE:
            return source_type.value
        mapping = {
            IngestionSourceType.MEETING: Mod3SourceType.MEETING,
            IngestionSourceType.VOICE_NOTE: Mod3SourceType.VOICE_NOTE,
            IngestionSourceType.DOCUMENT: Mod3SourceType.DOCUMENT,
            IngestionSourceType.EMAIL: Mod3SourceType.EMAIL,
            IngestionSourceType.CHAT: Mod3SourceType.CHAT,
        }
        return mapping.get(source_type, Mod3SourceType.DOCUMENT)

    def _persist_to_module3(
        self,
        db: Optional[Session],
        company_id: Optional[str],
        project_id: Optional[str],
        author_id: Optional[str],
        title: str,
        source_type: IngestionSourceType,
        raw_content: str,
        metadata: Dict[str, Any]
    ) -> tuple[str, bool]:
        """
        Safely registers source in Module 3 if db session and company_id are provided.
        Falls back to generating an independent local UUID if Module 3 is not used.
        """
        if db is not None and company_id and MODULE_3_AVAILABLE and memory_service is not None:
            try:
                mod3_st = self._map_source_type_to_mod3(source_type)
                source_req = SourceCreate(
                    company_id=company_id,
                    project_id=project_id,
                    author_id=author_id,
                    title=title,
                    source_type=mod3_st,
                    raw_content=raw_content,
                    meta_info=metadata
                )
                source = memory_service.create_source(db, source_req)
                return source.id, True
            except Exception as e:
                logger.warning(f"Module 3 source persistence skipped or failed: {e}")
                raise

        # Standalone operation (no DB required)
        standalone_id = f"standalone-{uuid.uuid4()}"
        return standalone_id, False

    def _dispatch_extraction(
        self,
        company_id: Optional[str],
        source_id: str,
        extracted_text: str,
        filename: Optional[str],
        source_type: str,
        project_id: Optional[str],
        author_id: Optional[str],
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatches standardized text to Module 2 using exact ExtractionRequest contract.
        Optional: does not block ingestion if Module 2 is unavailable or unconfigured.
        """
        if not MODULE_2_AVAILABLE or memory_extractor is None or not company_id:
            logger.info("Module 2 extraction skipped: Module 2 not available or company_id missing.")
            return None

        try:
            req = ExtractionRequest(
                company_id=company_id,
                source_id=source_id,
                extracted_text=extracted_text,
                filename=filename,
                source_type=source_type,
                project_id=project_id,
                author_id=author_id,
                metadata=metadata
            )
            extraction_resp = memory_extractor.extract(req)
            return extraction_resp.model_dump(mode="json")
        except Exception as e:
            logger.warning(f"Module 2 extraction skipped: {e}")
            return {"error": str(e), "status": "skipped"}

    def ingest_text(
        self,
        req: TextIngestRequest,
        db: Optional[Session] = None
    ) -> IngestionResponse:
        """Ingests raw text, meeting transcript, or chat conversation directly."""
        cleaned_text, stats = text_normalizer.normalize(req.text, req.title)

        meta = dict(req.metadata)
        meta.update(stats)
        if req.filename:
            meta["original_filename"] = req.filename

        # Persist to Module 3 (Optional)
        source_id, persisted = self._persist_to_module3(
            db=db,
            company_id=req.company_id,
            project_id=req.project_id,
            author_id=req.author_id,
            title=req.title,
            source_type=req.source_type,
            raw_content=cleaned_text,
            metadata=meta
        )

        # Trigger Module 2 Extraction (Optional)
        extraction_data = None
        if req.trigger_extraction and req.company_id:
            extraction_data = self._dispatch_extraction(
                company_id=req.company_id,
                source_id=source_id,
                extracted_text=cleaned_text,
                filename=req.filename,
                source_type=req.source_type.value,
                project_id=req.project_id,
                author_id=req.author_id,
                metadata=meta
            )

        return IngestionResponse(
            source_id=source_id,
            company_id=req.company_id,
            project_id=req.project_id,
            title=req.title,
            source_type=req.source_type.value,
            filename=req.filename,
            character_count=stats["character_count"],
            char_count=stats["character_count"],
            word_count=stats["word_count"],
            extracted_text=cleaned_text,
            transcription=cleaned_text,
            transcript=cleaned_text,
            preview=cleaned_text[:1000],
            persisted_to_storage=persisted,
            extraction_triggered=bool(req.trigger_extraction and req.company_id),
            extraction_result=extraction_data,
            status="completed",
            metadata=meta
        )

    def ingest_document(
        self,
        content: bytes,
        filename: str,
        company_id: Optional[str] = None,
        db: Optional[Session] = None,
        title: Optional[str] = None,
        project_id: Optional[str] = None,
        author_id: Optional[str] = None,
        source_type: IngestionSourceType = IngestionSourceType.DOCUMENT,
        trigger_extraction: bool = True,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResponse:
        """Parses and ingests a document (PDF, DOCX, TXT)."""
        parsed: DocumentParseResult = document_dispatcher.parse_document(content, filename)

        doc_title = title or f"Document: {filename}"
        meta = dict(parsed.metadata)
        if extra_metadata:
            meta.update(extra_metadata)
        meta["file_type"] = parsed.file_type

        # Persist to Module 3 (Optional)
        source_id, persisted = self._persist_to_module3(
            db=db,
            company_id=company_id,
            project_id=project_id,
            author_id=author_id,
            title=doc_title,
            source_type=source_type,
            raw_content=parsed.extracted_text,
            metadata=meta
        )

        # Trigger Module 2 Extraction (Optional)
        extraction_data = None
        if trigger_extraction and company_id:
            extraction_data = self._dispatch_extraction(
                company_id=company_id,
                source_id=source_id,
                extracted_text=parsed.extracted_text,
                filename=filename,
                source_type=source_type.value,
                project_id=project_id,
                author_id=author_id,
                metadata=meta
            )

        return IngestionResponse(
            source_id=source_id,
            company_id=company_id,
            project_id=project_id,
            title=doc_title,
            source_type=source_type.value,
            filename=filename,
            character_count=parsed.character_count,
            char_count=parsed.character_count,
            word_count=parsed.word_count,
            extracted_text=parsed.extracted_text,
            transcription=parsed.extracted_text,
            transcript=parsed.extracted_text,
            preview=parsed.extracted_text[:1000],
            persisted_to_storage=persisted,
            extraction_triggered=bool(trigger_extraction and company_id),
            extraction_result=extraction_data,
            status="completed",
            metadata=meta
        )

    def ingest_audio(
        self,
        audio_bytes: bytes,
        filename: str,
        company_id: Optional[str] = None,
        db: Optional[Session] = None,
        title: Optional[str] = None,
        project_id: Optional[str] = None,
        author_id: Optional[str] = None,
        language: Optional[str] = None,
        source_type: IngestionSourceType = IngestionSourceType.VOICE_NOTE,
        trigger_extraction: bool = True,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResponse:
        """Transcribes and ingests an audio recording (MP3, WAV, M4A)."""
        transcribed: AudioTranscribeResult = audio_transcription_manager.transcribe(
            audio_bytes=audio_bytes,
            filename=filename,
            language=language
        )

        audio_title = title or f"Audio Recording: {filename}"
        meta = dict(transcribed.metadata)
        if extra_metadata:
            meta.update(extra_metadata)
        meta["audio_format"] = transcribed.audio_format
        meta["duration_seconds"] = transcribed.duration_seconds
        meta["provider_used"] = transcribed.provider_used

        # Persist to Module 3 (Optional)
        source_id, persisted = self._persist_to_module3(
            db=db,
            company_id=company_id,
            project_id=project_id,
            author_id=author_id,
            title=audio_title,
            source_type=source_type,
            raw_content=transcribed.transcript,
            metadata=meta
        )

        # Trigger Module 2 Extraction (Optional)
        extraction_data = None
        if trigger_extraction and company_id:
            extraction_data = self._dispatch_extraction(
                company_id=company_id,
                source_id=source_id,
                extracted_text=transcribed.transcript,
                filename=filename,
                source_type=source_type.value,
                project_id=project_id,
                author_id=author_id,
                metadata=meta
            )

        return IngestionResponse(
            source_id=source_id,
            company_id=company_id,
            project_id=project_id,
            title=audio_title,
            source_type=source_type.value,
            filename=filename,
            character_count=transcribed.character_count,
            char_count=transcribed.character_count,
            word_count=transcribed.word_count,
            extracted_text=transcribed.transcript,
            transcription=transcribed.transcript,
            transcript=transcribed.transcript,
            preview=transcribed.transcript[:1000],
            persisted_to_storage=persisted,
            extraction_triggered=bool(trigger_extraction and company_id),
            extraction_result=extraction_data,
            status="completed",
            metadata=meta
        )


ingestion_service = IngestionService()
