from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TrackerStatus(str, Enum):
    OVERDUE = "overdue"
    DUE_SOON = "due_soon"
    PENDING = "pending"
    NO_DEADLINE = "no_deadline"
    COMPLETED = "completed"


class TrackedCommitment(BaseModel):
    """One employee commitment with its computed tracking status."""
    memory_id: str
    company_id: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    title: str
    description: str
    owner: Optional[str] = Field(None, description="Responsible person (Module 2 `person`, else memory author)")
    deadline: Optional[date] = Field(None, description="Resolved date; null when missing or unclear")
    deadline_text: Optional[str] = Field(None, description="Original phrase preserved by Module 2")
    deadline_needs_review: bool = Field(False, description="A deadline phrase exists but could not be resolved")
    days_left: Optional[int] = Field(None, description="Negative when overdue")
    tracker_status: TrackerStatus
    memory_status: str
    is_revised: bool = Field(False, description="This commitment replaced an earlier version")
    previous_deadline: Optional[date] = None
    source_id: str
    source_title: Optional[str] = None
    confidence: float
    created_at: datetime


class OwnerWorkload(BaseModel):
    owner: str
    open_count: int
    overdue_count: int
    due_soon_count: int
    commitments: List[TrackedCommitment]


class TrackerSummary(BaseModel):
    as_of: date
    total_open: int
    overdue: int
    due_soon: int
    pending: int
    no_deadline: int
    completed: int
    needs_review: int


class Reminder(BaseModel):
    memory_id: str
    owner: Optional[str]
    title: str
    deadline: date
    severity: Literal["overdue", "due_soon"]
    days_left: int = Field(..., description="Negative when overdue")
    message: str


class CommitmentChange(BaseModel):
    """A change between two consecutive versions of a commitment."""
    field: Literal["deadline", "owner"]
    old_value: Optional[str]
    new_value: Optional[str]
    from_memory_id: str
    to_memory_id: str
    changed_at: datetime
    reason: Optional[str] = None
    source_title: Optional[str] = None


class CommitmentChangeHistory(BaseModel):
    memory_id: str
    title: str
    current_deadline: Optional[date] = None
    versions_count: int
    changes: List[CommitmentChange]


class DecisionVersion(BaseModel):
    memory_id: str
    title: str
    content: str
    status: str
    created_at: datetime
    source_title: Optional[str] = None
    change_reason: Optional[str] = None


class DecisionChange(BaseModel):
    """A decision that was revised; versions run oldest to newest."""
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    current: DecisionVersion
    previous_versions: List[DecisionVersion]
    last_change_reason: Optional[str] = None
    changed_at: datetime


class CompleteRequest(BaseModel):
    company_id: str = Field(..., min_length=1, description="Company ID for tenant isolation")
    note: Optional[str] = Field(None, max_length=500)
