"""
Database-free tracker logic: status classification, grouping, reminders and
change detection. It works on Module 3 `MemoryResponse` objects, so it can be
tested without a database and reused by any caller.
"""
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

from memory_engine.schemas import MemoryResponse

from .deadline_parser import parse_deadline
from .schemas import (
    CommitmentChange,
    DecisionChange,
    DecisionVersion,
    OwnerWorkload,
    Reminder,
    TrackedCommitment,
    TrackerStatus,
    TrackerSummary,
)

UNASSIGNED = "Unassigned"
OPEN_STATUSES = (TrackerStatus.OVERDUE, TrackerStatus.DUE_SOON, TrackerStatus.PENDING, TrackerStatus.NO_DEADLINE)


# -------------------------------------------------------------
# Single-item helpers
# -------------------------------------------------------------
def resolve_owner(memory: MemoryResponse, people: Dict[str, str]) -> Optional[str]:
    """Owner = Module 2 `person` or `assignee`; otherwise the memory author's name."""
    person = memory.meta_info.get("person") or memory.meta_info.get("assignee")
    if isinstance(person, str) and person.strip():
        return person.strip()
    if memory.author_id and people.get(memory.author_id):
        return people[memory.author_id]
    return None


def resolve_deadline(memory: MemoryResponse) -> Tuple[Optional[str], Optional[date]]:
    """Return (original phrase, resolved date) relative to when the memory was recorded."""
    raw = memory.meta_info.get("deadline")
    text = str(raw).strip() if raw is not None and str(raw).strip() else None
    return text, parse_deadline(text, memory.created_at.date())


def classify(
    deadline: Optional[date], completed: bool, today: date, due_soon_days: int
) -> Tuple[TrackerStatus, Optional[int]]:
    """Return (status, days_left). days_left is negative when overdue."""
    days_left = (deadline - today).days if deadline else None
    if completed:
        return TrackerStatus.COMPLETED, days_left
    if days_left is None:
        return TrackerStatus.NO_DEADLINE, None
    if days_left < 0:
        return TrackerStatus.OVERDUE, days_left
    if days_left <= due_soon_days:
        return TrackerStatus.DUE_SOON, days_left
    return TrackerStatus.PENDING, days_left


def build_tracked(
    memory: MemoryResponse,
    today: date,
    due_soon_days: int,
    people: Dict[str, str],
    previous: Optional[MemoryResponse] = None,
) -> TrackedCommitment:
    text, deadline = resolve_deadline(memory)
    status, days_left = classify(deadline, memory.status == "completed", today, due_soon_days)
    previous_deadline = resolve_deadline(previous)[1] if previous else None
    return TrackedCommitment(
        memory_id=memory.id,
        company_id=memory.company_id,
        project_id=memory.project_id,
        project_name=memory.project_name,
        title=memory.title,
        description=memory.content,
        owner=resolve_owner(memory, people),
        deadline=deadline,
        deadline_text=text,
        deadline_needs_review=bool(text) and deadline is None,
        days_left=days_left,
        tracker_status=status,
        memory_status=memory.status,
        is_revised=memory.previous_memory_id is not None,
        previous_deadline=previous_deadline,
        source_id=memory.source_id,
        source_title=memory.source_title,
        confidence=memory.confidence,
        created_at=memory.created_at,
    )


# -------------------------------------------------------------
# Collections
# -------------------------------------------------------------
def sort_items(items: Iterable[TrackedCommitment]) -> List[TrackedCommitment]:
    """Earliest deadline first; items without a deadline last."""
    return sorted(items, key=lambda i: (i.deadline is None, i.deadline or date.max, i.title.lower()))


def filter_items(
    items: Iterable[TrackedCommitment],
    owner: Optional[str] = None,
    status: Optional[TrackerStatus] = None,
) -> List[TrackedCommitment]:
    result = list(items)
    if owner and isinstance(owner, str) and owner.strip():
        wanted = owner.strip().lower()
        result = [i for i in result if (i.owner or UNASSIGNED).lower() == wanted]
    if status and isinstance(status, (TrackerStatus, str)):
        stat_val = status.value if hasattr(status, "value") else str(status)
        result = [i for i in result if i.tracker_status.value == stat_val]
    return result


def overdue_items(items: Iterable[TrackedCommitment]) -> List[TrackedCommitment]:
    """Most overdue first."""
    late = [i for i in items if i.tracker_status == TrackerStatus.OVERDUE]
    return sorted(late, key=lambda i: i.days_left)


def upcoming_items(items: Iterable[TrackedCommitment], within_days: int) -> List[TrackedCommitment]:
    """Open commitments due between today and `within_days` from today, soonest first."""
    soon = [
        i for i in items
        if i.tracker_status in OPEN_STATUSES and i.days_left is not None and 0 <= i.days_left <= within_days
    ]
    return sorted(soon, key=lambda i: (i.days_left, i.title.lower()))


def group_by_owner(items: Iterable[TrackedCommitment]) -> List[OwnerWorkload]:
    """Open work per person; the busiest person first."""
    groups: Dict[str, List[TrackedCommitment]] = {}
    for item in items:
        if item.tracker_status in OPEN_STATUSES:
            groups.setdefault(item.owner or UNASSIGNED, []).append(item)
    result = [
        OwnerWorkload(
            owner=owner,
            open_count=len(rows),
            overdue_count=sum(1 for r in rows if r.tracker_status == TrackerStatus.OVERDUE),
            due_soon_count=sum(1 for r in rows if r.tracker_status == TrackerStatus.DUE_SOON),
            commitments=sort_items(rows),
        )
        for owner, rows in groups.items()
    ]
    return sorted(result, key=lambda w: (-w.overdue_count, -w.open_count, w.owner.lower()))


def summarize(items: Iterable[TrackedCommitment], today: date) -> TrackerSummary:
    rows = list(items)

    def count(status: TrackerStatus) -> int:
        return sum(1 for r in rows if r.tracker_status == status)

    open_rows = [r for r in rows if r.tracker_status in OPEN_STATUSES]
    return TrackerSummary(
        as_of=today,
        total_open=len(open_rows),
        overdue=count(TrackerStatus.OVERDUE),
        due_soon=count(TrackerStatus.DUE_SOON),
        pending=count(TrackerStatus.PENDING),
        no_deadline=count(TrackerStatus.NO_DEADLINE),
        completed=count(TrackerStatus.COMPLETED),
        needs_review=sum(1 for r in open_rows if r.deadline_needs_review),
    )


def make_reminders(items: Iterable[TrackedCommitment], within_days: int) -> List[Reminder]:
    """Overdue items (most overdue first), then items due within `within_days`."""
    reminders: List[Reminder] = []
    for item in overdue_items(items):
        late = -item.days_left
        reminders.append(Reminder(
            memory_id=item.memory_id,
            owner=item.owner,
            title=item.title,
            deadline=item.deadline,
            severity="overdue",
            days_left=item.days_left,
            message=(
                f"OVERDUE by {late} day{'s' if late != 1 else ''}: {item.owner or UNASSIGNED} - "
                f"{item.title} (was due {item.deadline:%d %b %Y})"
            ),
        ))
    for item in upcoming_items(items, within_days):
        if item.days_left == 0:
            when = "DUE TODAY"
        else:
            when = f"DUE in {item.days_left} day{'s' if item.days_left != 1 else ''}"
        reminders.append(Reminder(
            memory_id=item.memory_id,
            owner=item.owner,
            title=item.title,
            deadline=item.deadline,
            severity="due_soon",
            days_left=item.days_left,
            message=f"{when}: {item.owner or UNASSIGNED} - {item.title} ({item.deadline:%d %b %Y})",
        ))
    return reminders


# -------------------------------------------------------------
# Change detection (built on Module 3's version chain)
# -------------------------------------------------------------
def _deadline_value(memory: MemoryResponse) -> Tuple[Optional[str], Optional[date]]:
    text, parsed = resolve_deadline(memory)
    return (parsed.isoformat() if parsed else text), parsed


def build_change_history(timeline: List[MemoryResponse], people: Dict[str, str]) -> List[CommitmentChange]:
    """Compare consecutive versions (oldest first) and report deadline/owner changes."""
    changes: List[CommitmentChange] = []
    for older, newer in zip(timeline, timeline[1:]):
        old_label, old_date = _deadline_value(older)
        new_label, new_date = _deadline_value(newer)
        if old_date and new_date:
            deadline_changed = old_date != new_date
        else:
            deadline_changed = (old_label or "").lower() != (new_label or "").lower()
        common = dict(
            from_memory_id=older.id,
            to_memory_id=newer.id,
            changed_at=newer.created_at,
            reason=newer.change_reason,
            source_title=newer.source_title,
        )
        if deadline_changed:
            changes.append(CommitmentChange(field="deadline", old_value=old_label, new_value=new_label, **common))

        old_owner = resolve_owner(older, people)
        new_owner = resolve_owner(newer, people)
        if (old_owner or "").lower() != (new_owner or "").lower():
            changes.append(CommitmentChange(field="owner", old_value=old_owner, new_value=new_owner, **common))
    return changes


def _decision_version(memory: MemoryResponse) -> DecisionVersion:
    return DecisionVersion(
        memory_id=memory.id,
        title=memory.title,
        content=memory.content,
        status=memory.status,
        created_at=memory.created_at,
        source_title=memory.source_title,
        change_reason=memory.change_reason,
    )


def build_decision_change(timeline: List[MemoryResponse]) -> Optional[DecisionChange]:
    """Summarise a revised decision. Returns None if the decision was never revised."""
    if len(timeline) < 2:
        return None
    current = timeline[-1]
    return DecisionChange(
        project_id=current.project_id,
        project_name=current.project_name,
        current=_decision_version(current),
        previous_versions=[_decision_version(m) for m in timeline[:-1]],
        last_change_reason=current.change_reason,
        changed_at=current.created_at,
    )
