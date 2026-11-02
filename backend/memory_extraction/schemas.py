"""Validated input/output contracts for intelligent memory extraction."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    model_config = ConfigDict(extra="ignore")

    entity_type: EntityType = EntityType.OTHER
    name: str = Field(min_length=1, max_length=300)
    context: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_entity(cls, data: Any) -> Any:
        if isinstance(data, str):
            s = data.strip()
            if not s:
                s = "Unnamed Entity"
            return {"name": s, "entity_type": EntityType.OTHER.value}
        if isinstance(data, dict):
            name_val = str(data.get("name") or data.get("entity") or data.get("text") or "").strip()
            if not name_val:
                name_val = "Unnamed Entity"
            data["name"] = name_val[:300]

            raw_type = str(data.get("entity_type") or data.get("type") or "other").strip().lower()
            valid_types = {e.value for e in EntityType}
            if raw_type in valid_types:
                data["entity_type"] = raw_type
            else:
                alias_map = {
                    "people": EntityType.PERSON.value,
                    "human": EntityType.PERSON.value,
                    "user": EntityType.PERSON.value,
                    "org": EntityType.ORGANIZATION.value,
                    "corp": EntityType.COMPANY.value,
                    "corporation": EntityType.COMPANY.value,
                    "business": EntityType.COMPANY.value,
                    "client": EntityType.COMPANY.value,
                    "money": EntityType.FINANCIAL_AMOUNT.value,
                    "amount": EntityType.FINANCIAL_AMOUNT.value,
                    "currency": EntityType.FINANCIAL_AMOUNT.value,
                    "time": EntityType.DATE.value,
                    "datetime": EntityType.DATE.value,
                    "deadline": EntityType.DATE.value,
                }
                data["entity_type"] = alias_map.get(raw_type, EntityType.OTHER.value)
        return data


class ExtractionRequest(BaseModel):
    """Text and identifiers supplied by the ingestion/source pipeline."""
    company_id: str = Field(default="default-org")
    source_id: str = Field(default="")
    extracted_text: str = Field(..., min_length=1)
    text: str | None = None
    title: str | None = None
    filename: str | None = None
    source_type: str | None = None
    project_id: str | None = None
    author_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any):
        if isinstance(data, dict):
            if "text" in data and not data.get("extracted_text"):
                data["extracted_text"] = data["text"]
            if not data.get("source_id"):
                import uuid
                data["source_id"] = f"src-{uuid.uuid4().hex[:8]}"
            if not data.get("company_id"):
                data["company_id"] = "default-org"
        return data

    @field_validator("extracted_text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value or not str(value).strip():
            raise ValueError("extracted_text cannot be blank")
        return str(value).strip()



class ExtractedMemory(BaseModel):
    """One atomic business memory; auxiliary fields are retained in meta_info."""
    model_config = ConfigDict(extra="ignore")

    memory_type: MemoryType = MemoryType.GENERAL_INFO
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    person: str | None = None
    company: str | None = None
    project: str | None = None
    deadline: str | None = None
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    entities: list[EntityMention] = Field(default_factory=list)
    meta_info: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, str):
            val = data.strip()
            if not val:
                val = "Business Discussion Point"
            return {
                "memory_type": MemoryType.GENERAL_INFO.value,
                "title": val[:60],
                "content": val,
                "confidence": 0.85,
            }

        # Coerce any unexpected non-dict type into a minimal valid dict
        if not isinstance(data, dict):
            return {
                "memory_type": MemoryType.GENERAL_INFO.value,
                "title": "Business Discussion Point",
                "content": str(data) if data is not None else "Business fact extracted from transcript/notes.",
                "confidence": 0.85,
            }

        if isinstance(data, dict):
            # Known top-level fields
            known_keys = {
                "memory_type", "title", "content", "person", "company",
                "project", "deadline", "confidence", "tags", "entities", "meta_info"
            }
            # Put extra LLM keys into meta_info
            extra_meta = dict(data.get("meta_info") or {})
            for k, v in list(data.items()):
                if k not in known_keys and v is not None:
                    extra_meta[k] = v
            data["meta_info"] = extra_meta

            # Normalize title and content
            t = str(data.get("title") or "").strip()
            c = str(data.get("content") or "").strip()
            if not t and c:
                t = c[:60]
            elif not c and t:
                c = t
            elif not t and not c:
                t = "Business Discussion Point"
                c = "Business fact extracted from transcript/notes."
            data["title"] = t[:255]
            data["content"] = c

            # Normalize confidence (scale 0-100 down to 0-1 only if returned as percentage >= 5.0)
            conf = data.get("confidence")
            if conf is None:
                data["confidence"] = 0.95
            elif isinstance(conf, (int, float)):
                if 5.0 <= conf <= 100.0:
                    data["confidence"] = conf / 100.0
                else:
                    data["confidence"] = float(conf)

            # Normalize memory_type
            raw_type = data.get("memory_type")
            if hasattr(raw_type, "value"):
                m_type = str(raw_type.value).strip().lower()
            else:
                m_type = str(raw_type or "").strip().lower()
            if "." in m_type:
                m_type = m_type.split(".")[-1]

            valid_types = {e.value for e in MemoryType}
            aliases = {
                "commitment": MemoryType.EMPLOYEE_COMMITMENT.value,
                "commitments": MemoryType.EMPLOYEE_COMMITMENT.value,
                "employee_commitment": MemoryType.EMPLOYEE_COMMITMENT.value,
                "employee_commitments": MemoryType.EMPLOYEE_COMMITMENT.value,
                "action_item": MemoryType.EMPLOYEE_COMMITMENT.value,
                "requirement": MemoryType.CLIENT_REQUIREMENT.value,
                "requirements": MemoryType.CLIENT_REQUIREMENT.value,
                "client_requirement": MemoryType.CLIENT_REQUIREMENT.value,
                "client_requirements": MemoryType.CLIENT_REQUIREMENT.value,
                "deadline": MemoryType.IMPORTANT_DEADLINE.value,
                "deadlines": MemoryType.IMPORTANT_DEADLINE.value,
                "important_deadline": MemoryType.IMPORTANT_DEADLINE.value,
                "milestone": MemoryType.IMPORTANT_DEADLINE.value,
                "discussion": MemoryType.MEETING_DISCUSSION.value,
                "discussions": MemoryType.MEETING_DISCUSSION.value,
                "meeting_discussion": MemoryType.MEETING_DISCUSSION.value,
                "meeting": MemoryType.MEETING_DISCUSSION.value,
                "decision": MemoryType.DECISION.value,
                "decisions": MemoryType.DECISION.value,
                "general": MemoryType.GENERAL_INFO.value,
                "info": MemoryType.GENERAL_INFO.value,
                "general_info": MemoryType.GENERAL_INFO.value,
            }
            if m_type in valid_types:
                data["memory_type"] = m_type
            elif m_type in aliases:
                data["memory_type"] = aliases[m_type]
            elif not m_type:
                data["memory_type"] = MemoryType.GENERAL_INFO.value
            else:
                data["memory_type"] = m_type

            # Filter entities inside memory if any are blank strings
            raw_ents = data.get("entities")
            if isinstance(raw_ents, list):
                data["entities"] = [e for e in raw_ents if e and (not isinstance(e, str) or e.strip())]

        return data

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
    source_summary: str | None = None
    module3_payloads: list[dict[str, Any]] = Field(default_factory=list)
    processing_status: str = "completed"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_note: str = (
        "Confidence is an LLM-estimated score, not a calibrated probability."
    )

    def integration_payloads(self, request: ExtractionRequest) -> list[dict[str, Any]]:
        return [memory.to_memory_create_payload(request) for memory in self.memories]
