from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    company_id: Optional[str] = Field(
        default=None,
        description="Company UUID for Module 3 multi-tenant persistence (optional for standalone parsing)"
    )
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
    source_id: Optional[str] = Field(default=None, description="UUID of the persisted source in Module 3")
    company_id: Optional[str] = None
    project_id: Optional[str] = None
    title: str
    source_type: str
    filename: Optional[str] = None
    character_count: int = 0
    char_count: Optional[int] = None
    word_count: int = 0
    extracted_text: str = ""
    transcription: Optional[str] = None
    transcript: Optional[str] = None
    preview: Optional[str] = None
    persisted_to_storage: bool = False
    extraction_triggered: bool = False
    extraction_result: Optional[Dict[str, Any]] = None
    status: str = "completed"
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            text = (
                data.get("extracted_text")
                or data.get("transcription")
                or data.get("transcript")
                or data.get("preview")
                or ""
            )
            data["extracted_text"] = text
            data["transcription"] = text
            data["transcript"] = text
            data["preview"] = text[:1000] if text else ""

            chars = data.get("character_count")
            if chars is None:
                chars = data.get("char_count")
            if chars is None:
                chars = len(text)
            data["character_count"] = chars
            data["char_count"] = chars

            if "word_count" not in data or data["word_count"] is None:
                data["word_count"] = len(text.split()) if text else 0
        return data


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
