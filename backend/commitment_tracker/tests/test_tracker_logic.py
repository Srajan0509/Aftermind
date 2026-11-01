"""
Database-free tests for Module 4: deadline parsing, status classification,
grouping, reminders and change detection.

Run from `backend/`:  python -m pytest commitment_tracker/tests/test_tracker_logic.py -v
"""
from datetime import date, datetime

import pytest

from commitment_tracker import tracker_logic as logic
from commitment_tracker.deadline_parser import parse_deadline
from commitment_tracker.schemas import TrackerStatus
from memory_engine.schemas import MemoryCreate, MemoryResponse

TODAY = date(2026, 10, 31)  # a Saturday
DUE_SOON = 3


def make_memory(
    id="m1",
    title="Complete the project",
    memory_type="employee_commitment",
    status="active",
    meta=None,
    created=datetime(2026, 10, 20, 10, 0),  # a Tuesday
    author_id=None,
    previous=None,
    reason=None,
    source_title="Meeting 1",
    content="Task details",
):
    return MemoryResponse(
        id=id, company_id="c1", project_id="p1", source_id="s1", author_id=author_id,
        memory_type=memory_type, title=title, content=content, status=status,
        confidence=0.9, previous_memory_id=previous, change_reason=reason, tags=[],
        meta_info=meta or {}, created_at=created, updated_at=created,
        source_title=source_title, source_type="meeting", project_name="E-Commerce", company_name="ABC",
    )


def tracked(id="m1", person="Srajan", deadline="15 November 2026", status="active", **kw):
    meta = {}
    if person:
        meta["person"] = person
    if deadline:
        meta["deadline"] = deadline
    memory = make_memory(id=id, meta=meta, status=status, **kw)
    return logic.build_tracked(memory, TODAY, DUE_SOON, {})


# -------------------------------------------------------------
# Deadline parser
# -------------------------------------------------------------
@pytest.mark.parametrize("text, expected", [
    ("15 November 2026", date(2026, 11, 15)),
    ("November 15, 2026", date(2026, 11, 15)),
    ("by 15th of November", date(2026, 11, 15)),
    ("15 Nov", date(2026, 11, 15)),
    ("2026-11-20", date(2026, 11, 20)),
    ("2026-11-05", date(2026, 11, 5)),      # must stay November 5, not May 11
    ("15/11/2026", date(2026, 11, 15)),
    ("05/11/2026", date(2026, 11, 5)),      # day-first
    ("1 Jan", date(2027, 1, 1)),            # already past this year -> next year
    ("November 2026", date(2026, 11, 30)),  # month only -> end of month
    ("tomorrow", date(2026, 11, 1)),
    ("day after tomorrow", date(2026, 11, 2)),
    ("in 3 days", date(2026, 11, 3)),
    ("in 2 weeks", date(2026, 11, 14)),
    ("Friday", date(2026, 11, 6)),
    ("next Friday", date(2026, 11, 6)),
    ("next Saturday", date(2026, 11, 7)),   # anchor is a Saturday -> a week later
    ("end of the month", date(2026, 10, 31)),
])
def test_parse_deadline_resolves(text, expected):
    assert parse_deadline(text, TODAY) == expected


@pytest.mark.parametrize("text", ["", "   ", None, "soon", "ASAP", "by Q3", "next week", "marketing review", "may be soon", "29 Feb"])
def test_parse_deadline_returns_none_when_unclear(text):
    assert parse_deadline(text, TODAY) is None


def test_parse_deadline_year_rollover_from_december():
    assert parse_deadline("15 November", date(2026, 12, 5)) == date(2027, 11, 15)


# -------------------------------------------------------------
# Status classification
# -------------------------------------------------------------
@pytest.mark.parametrize("deadline, completed, expected, days_left", [
    (date(2026, 10, 30), False, TrackerStatus.OVERDUE, -1),
    (date(2026, 10, 31), False, TrackerStatus.DUE_SOON, 0),
    (date(2026, 11, 3), False, TrackerStatus.DUE_SOON, 3),
    (date(2026, 11, 4), False, TrackerStatus.PENDING, 4),
    (None, False, TrackerStatus.NO_DEADLINE, None),
    (date(2026, 10, 1), True, TrackerStatus.COMPLETED, -30),
])
def test_classify(deadline, completed, expected, days_left):
    assert logic.classify(deadline, completed, TODAY, DUE_SOON) == (expected, days_left)


def test_build_tracked_owner_and_deadline():
    item = tracked(person="Srajan", deadline="15 November 2026")
    assert item.owner == "Srajan"
    assert item.deadline == date(2026, 11, 15)
    assert item.tracker_status == TrackerStatus.PENDING
    assert item.deadline_needs_review is False
    assert item.is_revised is False


def test_owner_falls_back_to_author_then_unassigned():
    memory = make_memory(author_id="u1", meta={})
    assert logic.resolve_owner(memory, {"u1": "Riya"}) == "Riya"
    assert logic.resolve_owner(make_memory(meta={}), {}) is None


def test_unresolvable_deadline_is_flagged_for_review():
    item = tracked(deadline="by Q3")
    assert item.deadline is None
    assert item.deadline_text == "by Q3"
    assert item.deadline_needs_review is True
    assert item.tracker_status == TrackerStatus.NO_DEADLINE


def test_relative_deadline_uses_the_day_the_memory_was_recorded():
    # Recorded on Tuesday 2026-10-20, "next Friday" means 2026-10-23, not a date relative to today.
    item = tracked(deadline="next Friday")
    assert item.deadline == date(2026, 10, 23)
    assert item.tracker_status == TrackerStatus.OVERDUE


def test_completed_memory_status_wins_over_deadline():
    item = tracked(deadline="1 October 2026", status="completed")
    assert item.tracker_status == TrackerStatus.COMPLETED


# -------------------------------------------------------------
# Collections, reminders, summary
# -------------------------------------------------------------
def sample_items():
    return [
        tracked("a", "Aman", "28 October 2026", title="Send the budget estimate"),   # overdue 3d
        tracked("b", "Riya", "2 November 2026", title="Share revised proposal"),      # due in 2d
        tracked("c", "Srajan", "20 November 2026", title="Complete the project"),     # pending
        tracked("d", None, None, title="Review contract"),                            # no deadline, unassigned
        tracked("e", "Aman", "1 October 2026", title="Old task", status="completed"),
        tracked("f", "Riya", "by Q3", title="Plan Q3 roadmap"),                       # needs review
    ]


def test_overdue_and_upcoming_ordering():
    items = sample_items()
    assert [i.memory_id for i in logic.overdue_items(items)] == ["a"]
    assert [i.memory_id for i in logic.upcoming_items(items, 7)] == ["b"]
    assert [i.memory_id for i in logic.upcoming_items(items, 30)] == ["b", "c"]


def test_sort_puts_missing_deadlines_last():
    ordered = [i.memory_id for i in logic.sort_items(sample_items())]
    assert ordered[:3] == ["e", "a", "b"]
    assert set(ordered[-2:]) == {"d", "f"}


def test_group_by_owner_excludes_completed_and_marks_unassigned():
    groups = {g.owner: g for g in logic.group_by_owner(sample_items())}
    assert set(groups) == {"Aman", "Riya", "Srajan", "Unassigned"}
    assert groups["Aman"].open_count == 1 and groups["Aman"].overdue_count == 1
    assert groups["Riya"].open_count == 2 and groups["Riya"].due_soon_count == 1
    assert logic.group_by_owner(sample_items())[0].owner == "Aman"  # overdue work first


def test_filter_by_owner_is_case_insensitive_and_by_status():
    items = sample_items()
    assert {i.memory_id for i in logic.filter_items(items, owner="aman")} == {"a", "e"}
    assert [i.memory_id for i in logic.filter_items(items, owner="unassigned")] == ["d"]
    assert [i.memory_id for i in logic.filter_items(items, status=TrackerStatus.OVERDUE)] == ["a"]


def test_summary_counts():
    summary = logic.summarize(sample_items(), TODAY)
    assert summary.as_of == TODAY
    assert summary.total_open == 5
    assert (summary.overdue, summary.due_soon, summary.pending) == (1, 1, 1)
    assert summary.no_deadline == 2
    assert summary.completed == 1
    assert summary.needs_review == 1


def test_reminders_messages_and_order():
    reminders = logic.make_reminders(sample_items(), within_days=3)
    assert [r.severity for r in reminders] == ["overdue", "due_soon"]
    assert reminders[0].message == "OVERDUE by 3 days: Aman - Send the budget estimate (was due 28 Oct 2026)"
    assert reminders[0].days_left == -3
    assert reminders[1].message == "DUE in 2 days: Riya - Share revised proposal (02 Nov 2026)"


def test_reminders_due_today_and_none_when_all_clear():
    today_item = tracked("t", "Aman", "31 October 2026", title="Ship the build")
    assert logic.make_reminders([today_item], 3)[0].message.startswith("DUE TODAY: Aman - Ship the build")
    assert logic.make_reminders([tracked(deadline="1 December 2026")], 3) == []


# -------------------------------------------------------------
# Change detection
# -------------------------------------------------------------
def test_deadline_change_detected_across_versions():
    v1 = make_memory("v1", meta={"person": "Srajan", "deadline": "15 November 2026"}, status="superseded")
    v2 = make_memory(
        "v2", meta={"person": "Srajan", "deadline": "20 November 2026"}, previous="v1",
        created=datetime(2026, 10, 30, 9, 0), reason="Client asked for more testing", source_title="Meeting 3",
    )
    changes = logic.build_change_history([v1, v2], {})
    assert len(changes) == 1
    change = changes[0]
    assert (change.field, change.old_value, change.new_value) == ("deadline", "2026-11-15", "2026-11-20")
    assert change.reason == "Client asked for more testing"
    assert change.source_title == "Meeting 3"
    assert (change.from_memory_id, change.to_memory_id) == ("v1", "v2")


def test_same_date_written_differently_is_not_a_change():
    v1 = make_memory("v1", meta={"person": "Srajan", "deadline": "15 November 2026"})
    v2 = make_memory("v2", meta={"person": "Srajan", "deadline": "2026-11-15"}, previous="v1")
    assert logic.build_change_history([v1, v2], {}) == []


def test_owner_change_detected():
    v1 = make_memory("v1", meta={"person": "Aman", "deadline": "15 November 2026"})
    v2 = make_memory("v2", meta={"person": "Riya", "deadline": "15 November 2026"}, previous="v1")
    changes = logic.build_change_history([v1, v2], {})
    assert [(c.field, c.old_value, c.new_value) for c in changes] == [("owner", "Aman", "Riya")]


def test_previous_deadline_exposed_on_revised_commitment():
    v1 = make_memory("v1", meta={"deadline": "15 November 2026"})
    v2 = make_memory("v2", meta={"deadline": "20 November 2026"}, previous="v1")
    item = logic.build_tracked(v2, TODAY, DUE_SOON, {}, previous=v1)
    assert item.is_revised is True
    assert item.previous_deadline == date(2026, 11, 15)
    assert item.deadline == date(2026, 11, 20)


def test_decision_change_summary():
    old = make_memory("d1", title="Use Stripe", memory_type="decision", status="superseded", content="Stripe only")
    new = make_memory(
        "d2", title="Use Stripe and PayPal", memory_type="decision", previous="d1",
        reason="Client wants PayPal too", created=datetime(2026, 10, 28, 9, 0), content="Both gateways",
    )
    change = logic.build_decision_change([old, new])
    assert change.current.memory_id == "d2"
    assert [v.memory_id for v in change.previous_versions] == ["d1"]
    assert change.last_change_reason == "Client wants PayPal too"
    assert logic.build_decision_change([new]) is None


# -------------------------------------------------------------
# Contract with Module 2 (extraction) and Module 3 (memory store)
# -------------------------------------------------------------
def test_module2_payload_matches_module3_contract_and_module4_reads_it():
    from memory_extraction.schemas import ExtractedMemory, ExtractionRequest

    request = ExtractionRequest(company_id="c1", source_id="s1", extracted_text="Srajan will finish the project by 15 November.")
    extracted = ExtractedMemory(
        memory_type="employee_commitment",
        title="Complete the project",
        content="Srajan will complete the project by 15 November.",
        person="Srajan",
        deadline="15 November",
        confidence=0.9,
    )
    payload = extracted.to_memory_create_payload(request)
    MemoryCreate(**payload)  # Module 3 accepts Module 2's payload unchanged

    item = tracked(person=payload["meta_info"]["person"], deadline=payload["meta_info"]["deadline"])
    assert item.owner == "Srajan"
    assert item.deadline == date(2026, 11, 15)
