from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator


class SourceType(str, Enum):
    MEETING = "meeting"
    VOICE_NOTE = "voice_note"
    DOCUMENT = "document"
    EMAIL = "email"
    CHAT = "chat"


class MemoryType(str, Enum):
    DECISION = "decision"
    CLIENT_REQUIREMENT = "client_requirement"
    EMPLOYEE_COMMITMENT = "employee_commitment"
    IMPORTANT_DEADLINE = "important_deadline"
    MEETING_DISCUSSION = "meeting_discussion"
    GENERAL_INFO = "general_info"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    MODIFIED = "modified"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RelationshipType(str, Enum):
    SUPERSEDES = "supersedes"
    UPDATES = "updates"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"
    RELATES_TO = "relates_to"
    DERIVED_FROM = "derived_from"


# -------------------------------------------------------------
# Company Schemas
# -------------------------------------------------------------
class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    domain: Optional[str] = None


class CompanyResponse(BaseModel):
    id: str
    name: str
    domain: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Project Schemas
# -------------------------------------------------------------
class ProjectCreate(BaseModel):
    company_id: str
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = "active"


class ProjectResponse(BaseModel):
    id: str
    company_id: str
    name: str
    description: Optional[str]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Person Schemas
# -------------------------------------------------------------
class PersonCreate(BaseModel):
    company_id: str
    name: str = Field(..., min_length=2, max_length=255)
    email: Optional[str] = None
    role: Optional[str] = None


class PersonResponse(BaseModel):
    id: str
    company_id: str
    name: str
    email: Optional[str]
    role: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Source Schemas
# -------------------------------------------------------------
class SourceCreate(BaseModel):
    company_id: str
    project_id: Optional[str] = None
    author_id: Optional[str] = None
    title: str = Field(..., min_length=2, max_length=255)
    source_type: SourceType = SourceType.MEETING
    raw_content: str = Field(..., min_length=1, description="Original raw transcript or text")
    source_url: Optional[str] = None
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class SourceResponse(BaseModel):
    id: str
    company_id: str
    project_id: Optional[str]
    author_id: Optional[str]
    title: str
    source_type: str
    raw_content: str
    source_url: Optional[str]
    meta_info: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Memory Schemas
# -------------------------------------------------------------
class MemoryCreate(BaseModel):
    company_id: str = Field(..., description="Company ID for multi-tenant isolation")
    project_id: Optional[str] = Field(None, description="Optional Project ID")
    source_id: Optional[str] = Field(None, description="Source reference ID")
    author_id: Optional[str] = Field(None, description="Person who made the decision or commitment")
    memory_type: MemoryType = Field(..., description="Classification of the memory item")
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=2)
    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE)
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    previous_memory_id: Optional[str] = Field(None, description="ID of earlier memory being superseded or updated")
    change_reason: Optional[str] = Field(None, description="Reason for the revision or decision change")
    tags: List[str] = Field(default_factory=list)
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[MemoryStatus] = None
    change_reason: Optional[str] = None
    tags: Optional[List[str]] = None
    meta_info: Optional[Dict[str, Any]] = None


class MemoryResponse(BaseModel):
    id: str
    company_id: str
    project_id: Optional[str]
    source_id: Optional[str] = None
    author_id: Optional[str]
    memory_type: str
    title: str
    content: str
    status: str
    confidence: float
    previous_memory_id: Optional[str]
    change_reason: Optional[str]
    tags: List[str]
    meta_info: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    source_title: Optional[str] = None
    source_type: Optional[str] = None
    project_name: Optional[str] = None
    company_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Semantic Search Schemas
# -------------------------------------------------------------
class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    company_id: str = Field(default="default-org", description="Mandatory company ID to enforce data isolation")
    project_id: Optional[str] = Field(None, description="Filter by specific project")
    memory_type: Optional[MemoryType] = Field(None, description="Filter by memory classification")
    status: Optional[MemoryStatus] = Field(None, description="Filter by status (default considers all or active)")
    limit: int = Field(default=10, ge=1, le=50)
    min_similarity: float = Field(default=0.30, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    memory: MemoryResponse
    similarity_score: float
    source_reference: Optional[Dict[str, Any]] = None


class SemanticSearchResponse(BaseModel):
    query: str
    company_id: str
    results_count: int
    results: List[SearchResultItem]


# -------------------------------------------------------------
# RAG Chat Schemas
# -------------------------------------------------------------
class RAGChatRequest(BaseModel):
    question: Optional[str] = Field(None, description="User question about business memory")
    query: Optional[str] = Field(None, description="Alias for question")
    company_id: str = Field(default="default-org", description="Company ID for strict multi-tenant authorization")
    project_id: Optional[str] = Field(None, description="Optional project scope")
    include_superseded: bool = Field(default=False, description="Whether to include past superseded decisions")
    limit: int = Field(default=5, ge=1, le=20)
    conversation_history: Optional[List[Any]] = None

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def normalize_rag_request(cls, data: Any) -> Any:
        if isinstance(data, dict):
            q = data.get("question") or data.get("query") or ""
            data["question"] = q
            data["query"] = q
            if not data.get("company_id"):
                data["company_id"] = "default-org"
        return data


class SourceReference(BaseModel):
    source_id: Optional[str] = None
    source_title: Optional[str] = "Unspecified Source"
    source_type: Optional[str] = "document"
    memory_id: Optional[str] = None
    memory_title: Optional[str] = None
    memory_type: Optional[str] = None
    content_snippet: Optional[str] = ""
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(extra="ignore")


class RAGChatResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceReference]
    retrieved_memories_count: int
    is_grounded: bool


# -------------------------------------------------------------
# Relationship & History Schemas
# -------------------------------------------------------------
class MemoryRelationshipCreate(BaseModel):
    from_memory_id: str
    to_memory_id: str
    relationship_type: RelationshipType
    description: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class MemoryRelationshipResponse(BaseModel):
    id: str
    from_memory_id: str
    to_memory_id: str
    relationship_type: str
    description: Optional[str]
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemoryHistoryResponse(BaseModel):
    memory_id: str
    company_id: str
    current_status: str
    timeline: List[MemoryResponse]
    relationships: List[MemoryRelationshipResponse]
