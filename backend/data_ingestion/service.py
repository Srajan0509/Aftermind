import logging
import os
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

# Integration with Module 3 (Persistence)
from memory_engine.memory_service import memory_service
from memory_engine.schemas import SourceCreate, SourceType as Mod3SourceType

# Integration with Module 2 (Extraction)
try:
    from memory_extraction.extractor import memory_extractor, ExtractionError
    from memory_extraction.schemas import ExtractionRequest
    MODULE_2_AVAILABLE = True
except ImportError:
    MODULE_2_AVAILABLE = False
    memory_extractor = None

logger = logging.getLogger("data_ingestion.service")


class IngestionService:
    """
    Core orchestrator for Module 1: Multi-Source AI Data Ingestion.
    Standardizes inputs across documents, audio recordings, voice notes, and raw text.
    Persists sources in Module 3 and routes standardized payloads to Module 2.
    """

    def _map_source_type_to_mod3(self, source_type: IngestionSourceType) -> Mod3SourceType:
        """Ensures safe mapping between Module 1 and Module 3 source type enums."""
        mapping = {
            IngestionSourceType.MEETING: Mod3SourceType.MEETING,
            IngestionSourceType.VOICE_NOTE: Mod3SourceType.VOICE_NOTE,
            IngestionSourceType.DOCUMENT: Mod3SourceType.DOCUMENT,
            IngestionSourceType.EMAIL: Mod3SourceType.EMAIL,
            IngestionSourceType.CHAT: Mod3SourceType.CHAT,
        }
        return mapping.get(source_type, Mod3SourceType.DOCUMENT)

    def _dispatch_extraction(
        self,
        company_id: str,
        source_id: str,
        extracted_text: str,
        filename: Optional[str],
        source_type: str,
        project_id: Optional[str],
        author_id: Optional[str],
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Invokes Module 2 extraction pipeline if available."""
        if not MODULE_2_AVAILABLE or memory_extractor is None:
            logger.info("Module 2 extraction module is not available in environment.")
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
            logger.warning(f"Module 2 extraction skipped or failed: {e}")
            return {"error": str(e), "status": "failed"}

    def ingest_text(self, req: TextIngestRequest, db: Session) -> IngestionResponse:
        """Ingests raw text, meeting transcript, or chat conversation directly."""
        cleaned_text, stats = text_normalizer.normalize(req.text, req.title)

        meta = dict(req.metadata)
        meta.update(stats)
        if req.filename:
            meta["original_filename"] = req.filename

        # Register source in Module 3
        mod3_source_type = self._map_source_type_to_mod3(req.source_type)
        source = memory_service.create_source(db, SourceCreate(
            company_id=req.company_id,
            project_id=req.project_id,
            author_id=req.author_id,
            title=req.title,
            source_type=mod3_source_type,
            raw_content=cleaned_text,
            meta_info=meta
        ))

        # Optionally trigger Module 2 Extraction
        extraction_data = None
        if req.trigger_extraction:
            extraction_data = self._dispatch_extraction(
                company_id=req.company_id,
                source_id=source.id,
                extracted_text=cleaned_text,
                filename=req.filename,
                source_type=req.source_type.value,
                project_id=req.project_id,
                author_id=req.author_id,
                metadata=meta
            )

        return IngestionResponse(
            source_id=source.id,
            company_id=req.company_id,
            project_id=req.project_id,
            title=req.title,
            source_type=req.source_type.value,
            filename=req.filename,
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            extracted_text=cleaned_text,
            extraction_triggered=req.trigger_extraction,
            extraction_result=extraction_data,
            status="completed",
            metadata=meta
        )

    def ingest_document(
        self,
        content: bytes,
        filename: str,
        company_id: str,
        db: Session,
        title: Optional[str] = None,
        project_id: Optional[str] = None,
        author_id: Optional[str] = None,
        source_type: IngestionSourceType = IngestionSourceType.DOCUMENT,
        trigger_extraction: bool = True,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResponse:
        """Parses and ingests a document (.txt, .md, .pdf, .docx, .csv, .json)."""
        parsed: DocumentParseResult = document_dispatcher.parse_document(content, filename)

        doc_title = title or f"Document: {filename}"
        meta = dict(parsed.metadata)
        if extra_metadata:
            meta.update(extra_metadata)
        meta["file_type"] = parsed.file_type

        # Register source in Module 3
        mod3_source_type = self._map_source_type_to_mod3(source_type)
        source = memory_service.create_source(db, SourceCreate(
            company_id=company_id,
            project_id=project_id,
            author_id=author_id,
            title=doc_title,
            source_type=mod3_source_type,
            raw_content=parsed.extracted_text,
            meta_info=meta
        ))

        # Optionally trigger Module 2 Extraction
        extraction_data = None
        if trigger_extraction:
            extraction_data = self._dispatch_extraction(
                company_id=company_id,
                source_id=source.id,
                extracted_text=parsed.extracted_text,
                filename=filename,
                source_type=source_type.value,
                project_id=project_id,
                author_id=author_id,
                metadata=meta
            )

        return IngestionResponse(
            source_id=source.id,
            company_id=company_id,
            project_id=project_id,
            title=doc_title,
            source_type=source_type.value,
            filename=filename,
            character_count=parsed.character_count,
            word_count=parsed.word_count,
            extracted_text=parsed.extracted_text,
            extraction_triggered=trigger_extraction,
            extraction_result=extraction_data,
            status="completed",
            metadata=meta
        )

    def ingest_audio(
        self,
        audio_bytes: bytes,
        filename: str,
        company_id: str,
        db: Session,
        title: Optional[str] = None,
        project_id: Optional[str] = None,
        author_id: Optional[str] = None,
        language: Optional[str] = None,
        source_type: IngestionSourceType = IngestionSourceType.VOICE_NOTE,
        trigger_extraction: bool = True,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResponse:
        """Transcribes and ingests an audio recording (.mp3, .wav, .m4a, etc.)."""
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

        # Register source in Module 3
        mod3_source_type = self._map_source_type_to_mod3(source_type)
        source = memory_service.create_source(db, SourceCreate(
            company_id=company_id,
            project_id=project_id,
            author_id=author_id,
            title=audio_title,
            source_type=mod3_source_type,
            raw_content=transcribed.transcript,
            meta_info=meta
        ))

        # Optionally trigger Module 2 Extraction
        extraction_data = None
        if trigger_extraction:
            extraction_data = self._dispatch_extraction(
                company_id=company_id,
                source_id=source.id,
                extracted_text=transcribed.transcript,
                filename=filename,
                source_type=source_type.value,
                project_id=project_id,
                author_id=author_id,
                metadata=meta
            )

        return IngestionResponse(
            source_id=source.id,
            company_id=company_id,
            project_id=project_id,
            title=audio_title,
            source_type=source_type.value,
            filename=filename,
            character_count=transcribed.character_count,
            word_count=transcribed.word_count,
            extracted_text=transcribed.transcript,
            extraction_triggered=trigger_extraction,
            extraction_result=extraction_data,
            status="completed",
            metadata=meta
        )


ingestion_service = IngestionService()
