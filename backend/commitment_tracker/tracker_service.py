"""
Database-facing orchestration for Module 4.

Reads commitments and decisions through Module 3's `memory_service` (same
database, same tenant isolation) and delegates all computation to
`tracker_logic`. The only write is `complete_commitment`.
"""
import logging
from datetime import date, datetime, timezone
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from memory_engine.memory_service import memory_service
from memory_engine.models import Memory, Person
from memory_engine.schemas import MemoryResponse

from . import tracker_logic as logic
from .config import tracker_settings
from .schemas import (
    CommitmentChangeHistory,
    DecisionChange,
    OwnerWorkload,
    Reminder,
    TrackedCommitment,
    TrackerStatus,
    TrackerSummary,
)

logger = logging.getLogger("commitment_tracker.service")

COMMITMENT_TYPE = "employee_commitment"
DECISION_TYPE = "decision"
OPEN_MEMORY_STATUSES = ("active", "modified")  # superseded/cancelled are history, not open work


class CommitmentNotFoundError(LookupError):
    """Commitment does not exist for this company."""


class InvalidCommitmentStateError(ValueError):
    """Commitment exists but cannot be changed in its current state."""


class CommitmentTrackerService:
    # -------------------------------------------------------------
    # Internal data access
    # -------------------------------------------------------------
    def _fetch(
        self,
        db: Session,
        company_id: str,
        memory_type: str,
        statuses: Iterable[str],
        project_id: Optional[str] = None,
    ) -> List[MemoryResponse]:
        rows: List[MemoryResponse] = []
        for memory_status in statuses:
            rows.extend(memory_service.list_memories(
                db=db,
                company_id=company_id,
                project_id=project_id,
                memory_type=memory_type,
                status=memory_status,
                limit=tracker_settings.max_rows,
            ))
        return rows

    def _people_names(self, db: Session, company_id: str, memories: Iterable[MemoryResponse]) -> Dict[str, str]:
        ids = {m.author_id for m in memories if m.author_id}
        if not ids:
            return {}
        people = db.query(Person).filter(Person.company_id == company_id, Person.id.in_(ids)).all()
        return {p.id: p.name for p in people}

    def _previous_versions(
        self, db: Session, company_id: str, memories: Iterable[MemoryResponse]
    ) -> Dict[str, MemoryResponse]:
        previous: Dict[str, MemoryResponse] = {}
        for memory in memories:
            if memory.previous_memory_id:
                older = memory_service.get_memory(db, memory.previous_memory_id, company_id)
                if older:
                    previous[memory.id] = older
        return previous

    def _build_items(
        self, db: Session, company_id: str, memories: List[MemoryResponse], today: date
    ) -> List[TrackedCommitment]:
        people = self._people_names(db, company_id, memories)
        previous = self._previous_versions(db, company_id, memories)
        return [
            logic.build_tracked(m, today, tracker_settings.due_soon_days, people, previous.get(m.id))
            for m in memories
        ]

    # -------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------
    def list_commitments(
        self,
        db: Session,
        company_id: str,
        project_id: Optional[str] = None,
        owner: Optional[str] = None,
        status: Optional[TrackerStatus] = None,
        include_completed: bool = True,
        as_of: Optional[date] = None,
    ) -> List[TrackedCommitment]:
        """Latest version of every commitment with its tracking status."""
        today = as_of or date.today()
        include_completed = include_completed or status == TrackerStatus.COMPLETED
        statuses = OPEN_MEMORY_STATUSES + (("completed",) if include_completed else ())
        memories = self._fetch(db, company_id, COMMITMENT_TYPE, statuses, project_id)
        items = self._build_items(db, company_id, memories, today)
        return logic.sort_items(logic.filter_items(items, owner, status))

    def overdue(self, db: Session, company_id: str, project_id: Optional[str] = None,
                as_of: Optional[date] = None) -> List[TrackedCommitment]:
        items = self.list_commitments(db, company_id, project_id, include_completed=False, as_of=as_of)
        return logic.overdue_items(items)

    def upcoming(self, db: Session, company_id: str, within_days: Optional[int] = None,
                 project_id: Optional[str] = None, as_of: Optional[date] = None) -> List[TrackedCommitment]:
        window = tracker_settings.default_upcoming_days if within_days is None else within_days
        items = self.list_commitments(db, company_id, project_id, include_completed=False, as_of=as_of)
        return logic.upcoming_items(items, window)

    def by_owner(self, db: Session, company_id: str, project_id: Optional[str] = None,
                 as_of: Optional[date] = None) -> List[OwnerWorkload]:
        items = self.list_commitments(db, company_id, project_id, include_completed=False, as_of=as_of)
        return logic.group_by_owner(items)

    def reminders(self, db: Session, company_id: str, within_days: Optional[int] = None,
                  project_id: Optional[str] = None, as_of: Optional[date] = None) -> List[Reminder]:
        window = tracker_settings.due_soon_days if within_days is None else within_days
        items = self.list_commitments(db, company_id, project_id, include_completed=False, as_of=as_of)
        return logic.make_reminders(items, window)

    def summary(self, db: Session, company_id: str, project_id: Optional[str] = None,
                as_of: Optional[date] = None) -> TrackerSummary:
        today = as_of or date.today()
        items = self.list_commitments(db, company_id, project_id, include_completed=True, as_of=today)
        return logic.summarize(items, today)

    # -------------------------------------------------------------
    # Change detection (reuses Module 3's version chain)
    # -------------------------------------------------------------
    def commitment_changes(self, db: Session, company_id: str, memory_id: str) -> CommitmentChangeHistory:
        memory = memory_service.get_memory(db, memory_id=memory_id, company_id=company_id)
        if memory is None or memory.memory_type != COMMITMENT_TYPE:
            raise CommitmentNotFoundError(f"Commitment {memory_id} not found for this company.")

        history = memory_service.get_memory_history(db, memory_id=memory_id)
        timeline = history.timeline if history and history.timeline else [memory]
        people = self._people_names(db, company_id, timeline)
        latest = timeline[-1]
        return CommitmentChangeHistory(
            memory_id=latest.id,
            title=latest.title,
            current_deadline=logic.resolve_deadline(latest)[1],
            versions_count=len(timeline),
            changes=logic.build_change_history(timeline, people),
        )

    def decision_changes(self, db: Session, company_id: str, project_id: Optional[str] = None) -> List[DecisionChange]:
        """Current decisions that replaced an earlier decision, newest change first."""
        decisions = self._fetch(db, company_id, DECISION_TYPE, OPEN_MEMORY_STATUSES, project_id)
        changes: List[DecisionChange] = []
        for decision in decisions:
            if not decision.previous_memory_id:
                continue
            history = memory_service.get_memory_history(db, memory_id=decision.id)
            change = logic.build_decision_change(history.timeline) if history else None
            if change:
                changes.append(change)
        return sorted(changes, key=lambda c: c.changed_at, reverse=True)

    # -------------------------------------------------------------
    # Write: mark a commitment as completed
    # -------------------------------------------------------------
    def complete_commitment(
        self,
        db: Session,
        company_id: str,
        memory_id: str,
        note: Optional[str] = None,
        as_of: Optional[date] = None,
    ) -> TrackedCommitment:
        """Set a commitment's status to `completed` (a status Module 3 already defines)."""
        memory = db.query(Memory).filter(Memory.id == memory_id, Memory.company_id == company_id).first()
        if memory is None or memory.memory_type != COMMITMENT_TYPE:
            raise CommitmentNotFoundError(f"Commitment {memory_id} not found for this company.")

        if memory.status != "completed":
            if memory.status not in OPEN_MEMORY_STATUSES:
                raise InvalidCommitmentStateError(
                    f"Commitment is '{memory.status}' and cannot be marked completed."
                )
            details = dict(memory.meta_info or {})  # copy so SQLAlchemy detects the JSON change
            details["completed_at"] = datetime.now(timezone.utc).isoformat()
            if note:
                details["completion_note"] = note
            memory.meta_info = details
            memory.status = "completed"
            db.commit()
            logger.info("Commitment %s marked completed", memory_id)

        refreshed = memory_service.get_memory(db, memory_id=memory_id, company_id=company_id)
        return self._build_items(db, company_id, [refreshed], as_of or date.today())[0]


tracker_service = CommitmentTrackerService()
