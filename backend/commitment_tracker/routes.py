from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from memory_engine.database import get_db

from .schemas import (
    CommitmentChangeHistory,
    CompleteRequest,
    DecisionChange,
    OwnerWorkload,
    Reminder,
    TrackedCommitment,
    TrackerStatus,
    TrackerSummary,
)
from .tracker_service import (
    CommitmentNotFoundError,
    InvalidCommitmentStateError,
    tracker_service,
)

router = APIRouter(
    prefix="/api/tracker",
    tags=["Module 4: Commitment & Decision Tracker"],
)

CompanyId = Annotated[str, Query(min_length=1, description="Company ID required to enforce tenant isolation")]
ProjectId = Annotated[Optional[str], Query(description="Filter by project")]
AsOf = Annotated[
    Optional[date],
    Query(description="Evaluate deadlines as of this date (default: today). Useful for demos and tests."),
]


@router.get("/summary", response_model=TrackerSummary)
def get_summary(
    company_id: CompanyId,
    project_id: ProjectId = None,
    as_of: AsOf = None,
    db: Session = Depends(get_db),
):
    """Counts of open, overdue, due-soon and completed commitments."""
    return tracker_service.summary(db, company_id, project_id, as_of)


@router.get("/commitments", response_model=List[TrackedCommitment])
def list_commitments(
    company_id: CompanyId,
    project_id: ProjectId = None,
    owner: Optional[str] = Query(None, description="Filter by responsible person (case-insensitive)"),
    tracker_status: Optional[TrackerStatus] = Query(None, alias="status", description="Filter by tracking status"),
    include_completed: bool = Query(True, description="Include completed commitments"),
    as_of: AsOf = None,
    db: Session = Depends(get_db),
):
    """All commitments (latest version only) with deadline, owner and tracking status."""
    return tracker_service.list_commitments(
        db, company_id, project_id, owner, tracker_status, include_completed, as_of
    )


@router.get("/overdue", response_model=List[TrackedCommitment])
def list_overdue(
    company_id: CompanyId,
    project_id: ProjectId = None,
    as_of: AsOf = None,
    db: Session = Depends(get_db),
):
    """Open commitments whose deadline has passed, most overdue first."""
    return tracker_service.overdue(db, company_id, project_id, as_of)


@router.get("/upcoming", response_model=List[TrackedCommitment])
def list_upcoming(
    company_id: CompanyId,
    within_days: Optional[int] = Query(None, ge=0, le=365, description="Look-ahead window in days"),
    project_id: ProjectId = None,
    as_of: AsOf = None,
    db: Session = Depends(get_db),
):
    """Open commitments due soon, soonest first."""
    return tracker_service.upcoming(db, company_id, within_days, project_id, as_of)


@router.get("/by-owner", response_model=List[OwnerWorkload])
def list_by_owner(
    company_id: CompanyId,
    project_id: ProjectId = None,
    as_of: AsOf = None,
    db: Session = Depends(get_db),
):
    """Open commitments grouped by responsible employee."""
    return tracker_service.by_owner(db, company_id, project_id, as_of)


@router.get("/reminders", response_model=List[Reminder])
def list_reminders(
    company_id: CompanyId,
    within_days: Optional[int] = Query(None, ge=0, le=60, description="Remind for items due within this many days"),
    project_id: ProjectId = None,
    as_of: AsOf = None,
    db: Session = Depends(get_db),
):
    """Reminder messages for overdue and soon-due commitments (for the dashboard or a scheduler)."""
    return tracker_service.reminders(db, company_id, within_days, project_id, as_of)


@router.get("/commitments/{memory_id}/changes", response_model=CommitmentChangeHistory)
def get_commitment_changes(
    memory_id: str,
    company_id: CompanyId,
    db: Session = Depends(get_db),
):
    """Deadline and owner changes of a commitment across meetings."""
    try:
        return tracker_service.commitment_changes(db, company_id, memory_id)
    except CommitmentNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/decision-changes", response_model=List[DecisionChange])
def list_decision_changes(
    company_id: CompanyId,
    project_id: ProjectId = None,
    db: Session = Depends(get_db),
):
    """Decisions that were revised, with the full version history."""
    return tracker_service.decision_changes(db, company_id, project_id)


@router.post("/commitments/{memory_id}/complete", response_model=TrackedCommitment)
def complete_commitment(
    memory_id: str,
    req: CompleteRequest,
    as_of: AsOf = None,
    db: Session = Depends(get_db),
):
    """Mark a commitment as completed."""
    try:
        return tracker_service.complete_commitment(db, req.company_id, memory_id, req.note, as_of)
    except CommitmentNotFoundError as exc:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidCommitmentStateError as exc:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc))
