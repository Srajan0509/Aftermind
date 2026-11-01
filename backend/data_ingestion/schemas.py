from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class IngestionSourceType(str, Enum):
    MEETING = "meeting"
    VOICE_NOTE = "voice_note"
    DOCUMENT = "document"
    EMAIL = "email"
    CHAT = "chat"


class DocumentParseResult(BaseModel):
    """Result of parsing a document file into clean standardized text."""
    model_config = ConfigDict(extra="forbid")

    filename: str
    file_type: str
    character_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    extracted_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AudioTranscribeResult(BaseModel):
    """Result of transcribing an audio recording or voice note."""
    model_config = ConfigDict(extra="forbid")

    filename: str
    audio_format: str
    duration_seconds: Optional[float] = None
    language: Optional[str] = None
    transcript: str
    character_count: int = Field(ge=0)
    word_count: int = Field(ge=0)
    provider_used: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextIngestRequest(BaseModel):
    """Request payload for direct text or transcript ingestion."""
    company_id: str = Field(min_length=1, description="Company UUID for multi-tenant isolation")
    title: str = Field(min_length=2, max_length=255, description="Source descriptive title")
    text: str = Field(min_length=1, description="Raw text or transcript")
    source_type: IngestionSourceType = Field(default=IngestionSourceType.DOCUMENT)
    project_id: Optional[str] = Field(default=None, description="Optional Project UUID")
    author_id: Optional[str] = Field(default=None, description="Optional Author/Person UUID")
    filename: Optional[str] = Field(default=None, description="Optional original file name")
    trigger_extraction: bool = Field(
        default=True,
        description="Whether to forward standardized text to Module 2 for memory extraction"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("text cannot be blank or empty")
        return value.strip()


class IngestionResponse(BaseModel):
    """Comprehensive response for ingested sources across all formats."""
    source_id: str = Field(description="UUID of the persisted source in Module 3")
    company_id: str
    project_id: Optional[str] = None
    title: str
    source_type: str
    filename: Optional[str] = None
    character_count: int
    word_count: int
    extracted_text: str
    extraction_triggered: bool = False
    extraction_result: Optional[Dict[str, Any]] = None
    status: str = "completed"
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestionHealthResponse(BaseModel):
    """Health and capability reporting for Module 1."""
    status: str = "healthy"
    module: str = "Module 1: Multi-Source AI Data Ingestion"
    supported_document_types: List[str]
    supported_audio_types: List[str]
    transcriber_provider: str
    max_document_size_mb: float
    max_audio_size_mb: float
    max_input_characters: int
