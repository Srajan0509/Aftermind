"""Validated input/output contracts for intelligent memory extraction."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryType(str, Enum):
    DECISION = "decision"
    CLIENT_REQUIREMENT = "client_requirement"
    EMPLOYEE_COMMITMENT = "employee_commitment"
    IMPORTANT_DEADLINE = "important_deadline"
    MEETING_DISCUSSION = "meeting_discussion"
    GENERAL_INFO = "general_info"


class EntityType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    PROJECT = "project"
    ORGANIZATION = "organization"
    FINANCIAL_AMOUNT = "financial_amount"
    DATE = "date"
    OTHER = "other"


class EntityMention(BaseModel):
    entity_type: EntityType
    name: str = Field(min_length=1, max_length=300)
    context: str | None = None


class ExtractionRequest(BaseModel):
    """Text and identifiers supplied by the ingestion/source pipeline."""
    company_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    extracted_text: str = Field(min_length=1)
    filename: str | None = None
    source_type: str | None = None
    project_id: str | None = None
    author_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("extracted_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("extracted_text cannot be blank")
        return value.strip()


class ExtractedMemory(BaseModel):
    """One atomic business memory; auxiliary fields are retained in meta_info."""
    model_config = ConfigDict(extra="forbid")

    memory_type: MemoryType
    title: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=2)
    person: str | None = None
    company: str | None = None
    project: str | None = None
    deadline: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    entities: list[EntityMention] = Field(default_factory=list)
    meta_info: dict[str, Any] = Field(default_factory=dict)

    def to_memory_create_payload(self, request: ExtractionRequest) -> dict[str, Any]:
        """Map this extraction to Module 3's existing MemoryCreate contract."""
        details = dict(self.meta_info)
        details.update({
            "person": self.person,
            "company": self.company,
            "project": self.project or request.project_id,
            "deadline": self.deadline,
            "entities": [item.model_dump(mode="json") for item in self.entities],
            "extraction_module": "module_2",
            "source_filename": request.filename,
            "source_type": request.source_type,
        })
        # Do not send null values for optional entity details.
        details = {key: value for key, value in details.items() if value is not None}
        return {
            "company_id": request.company_id,
            "project_id": request.project_id,
            "source_id": request.source_id,
            "author_id": request.author_id,
            "memory_type": self.memory_type.value,
            "title": self.title,
            "content": self.content,
            "status": "active",
            "confidence": self.confidence,
            "tags": self.tags,
            "meta_info": details,
        }


class ExtractionResponse(BaseModel):
    company_id: str
    source_id: str
    memories: list[ExtractedMemory]
    entities: list[EntityMention]
    memories_count: int
    module3_payloads: list[dict[str, Any]] = Field(default_factory=list)
    processing_status: str = "completed"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_note: str = (
        "Confidence is an LLM-estimated score, not a calibrated probability."
    )

    def integration_payloads(self, request: ExtractionRequest) -> list[dict[str, Any]]:
        return [memory.to_memory_create_payload(request) for memory in self.memories]
