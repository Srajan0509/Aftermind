"""
Database + API tests for Module 4 (in-memory SQLite, same approach as Module 3's tests).

Run from `backend/`:  python -m pytest commitment_tracker/tests -v
Skipped automatically if FastAPI / SQLAlchemy / pydantic-settings are not installed.
"""
import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("fastapi")
pytest.importorskip("pydantic_settings")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from commitment_tracker.routes import router as tracker_router  # noqa: E402
from memory_engine.database import Base, get_db  # noqa: E402
from memory_engine.memory_service import memory_service  # noqa: E402
from memory_engine.routes import router as memory_router  # noqa: E402
from memory_engine.schemas import (  # noqa: E402
    CompanyCreate,
    MemoryCreate,
    MemoryType,
    PersonCreate,
    ProjectCreate,
    SourceCreate,
    SourceType,
)

AS_OF = "2026-10-31"

test_engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    app = FastAPI()
    app.include_router(memory_router)   # Module 3, used to ingest like the real pipeline
    app.include_router(tracker_router)  # Module 4

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


# -------------------------------------------------------------
# Seed helpers (all go through Module 3's public service)
# -------------------------------------------------------------
def seed_company(db, name="ABC Technologies"):
    company = memory_service.get_or_create_company(db, CompanyCreate(name=name))
    project = memory_service.get_or_create_project(db, ProjectCreate(company_id=company.id, name="E-Commerce Revamp"))
    source = memory_service.create_source(db, SourceCreate(
        company_id=company.id, project_id=project.id, title="Meeting 1",
        source_type=SourceType.MEETING, raw_content="Kickoff meeting transcript.",
    ))
    return company, project, source


def add_memory(db, company, project, source, title, memory_type=MemoryType.EMPLOYEE_COMMITMENT,
               person=None, deadline=None, author=None, previous=None, reason=None):
    meta = {}
    if person:
        meta["person"] = person
    if deadline:
        meta["deadline"] = deadline
    return memory_service.create_memory(db, MemoryCreate(
        company_id=company.id, project_id=project.id, source_id=source.id,
        author_id=author.id if author else None,
        memory_type=memory_type, title=title, content=f"Details for {title}",
        meta_info=meta, previous_memory_id=previous, change_reason=reason,
    ))


def get(client, path, company, **params):
    return client.get(f"/api/tracker{path}", params={"company_id": company.id, **params})


# -------------------------------------------------------------
# Listing and status classification
# -------------------------------------------------------------
def test_list_commitments_classifies_status(db, client):
    company, project, source = seed_company(db)
    add_memory(db, company, project, source, "Send budget estimate", person="Aman", deadline="28 October 2026")
    add_memory(db, company, project, source, "Share revised proposal", person="Riya", deadline="2 November 2026")
    add_memory(db, company, project, source, "Complete the project", person="Srajan", deadline="30 November 2026")
    add_memory(db, company, project, source, "Review contract", person="Nirmal")
    # Other memory types must not appear as commitments.
    add_memory(db, company, project, source, "Use Stripe", memory_type=MemoryType.DECISION)

    response = get(client, "/commitments", company, as_of=AS_OF)
    assert response.status_code == 200
    by_title = {row["title"]: row for row in response.json()}
    assert set(by_title) == {"Send budget estimate", "Share revised proposal", "Complete the project", "Review contract"}
    assert by_title["Send budget estimate"]["tracker_status"] == "overdue"
    assert by_title["Send budget estimate"]["days_left"] == -3
    assert by_title["Share revised proposal"]["tracker_status"] == "due_soon"
    assert by_title["Complete the project"]["tracker_status"] == "pending"
    assert by_title["Review contract"]["tracker_status"] == "no_deadline"

    summary = get(client, "/summary", company, as_of=AS_OF).json()
    assert (summary["total_open"], summary["overdue"], summary["due_soon"], summary["pending"], summary["no_deadline"]) == (4, 1, 1, 1, 1)

    assert [r["title"] for r in get(client, "/overdue", company, as_of=AS_OF).json()] == ["Send budget estimate"]
    assert [r["title"] for r in get(client, "/upcoming", company, as_of=AS_OF, within_days=7).json()] == ["Share revised proposal"]
    assert [r["title"] for r in get(client, "/commitments", company, as_of=AS_OF, owner="aman").json()] == ["Send budget estimate"]
    assert [r["title"] for r in get(client, "/commitments", company, as_of=AS_OF, status="overdue").json()] == ["Send budget estimate"]


def test_owner_falls_back_to_memory_author(db, client):
    company, project, source = seed_company(db)
    riya = memory_service.get_or_create_person(db, PersonCreate(company_id=company.id, name="Riya Sharma"))
    add_memory(db, company, project, source, "Prepare demo", author=riya, deadline="5 November 2026")
    add_memory(db, company, project, source, "Orphan task", deadline="6 November 2026")

    groups = {g["owner"]: g for g in get(client, "/by-owner", company, as_of=AS_OF).json()}
    assert set(groups) == {"Riya Sharma", "Unassigned"}
    assert groups["Riya Sharma"]["open_count"] == 1


def test_unresolvable_deadline_is_flagged(db, client):
    company, project, source = seed_company(db)
    add_memory(db, company, project, source, "Plan roadmap", person="Riya", deadline="by Q3")
    row = get(client, "/commitments", company, as_of=AS_OF).json()[0]
    assert row["deadline"] is None
    assert row["deadline_text"] == "by Q3"
    assert row["deadline_needs_review"] is True
    assert get(client, "/summary", company, as_of=AS_OF).json()["needs_review"] == 1


# -------------------------------------------------------------
# Deadline change tracking (uses Module 3's version chain)
# -------------------------------------------------------------
def test_deadline_change_is_tracked_with_history(db, client):
    company, project, source = seed_company(db)
    first = add_memory(db, company, project, source, "Complete the project", person="Srajan", deadline="15 November 2026")
    meeting3 = memory_service.create_source(db, SourceCreate(
        company_id=company.id, project_id=project.id, title="Meeting 3: Schedule Adjustment",
        source_type=SourceType.MEETING, raw_content="Deadline moved to 20 November.",
    ))
    revised = add_memory(
        db, company, project, meeting3, "Complete the project", person="Srajan",
        deadline="20 November 2026", previous=first.id, reason="Extra security testing needed",
    )

    rows = get(client, "/commitments", company, as_of=AS_OF).json()
    assert len(rows) == 1                      # superseded version is hidden, only the latest is tracked
    assert rows[0]["memory_id"] == revised.id
    assert rows[0]["deadline"] == "2026-11-20"
    assert rows[0]["is_revised"] is True
    assert rows[0]["previous_deadline"] == "2026-11-15"

    history = get(client, f"/commitments/{revised.id}/changes", company).json()
    assert history["versions_count"] == 2
    assert history["current_deadline"] == "2026-11-20"
    assert len(history["changes"]) == 1
    change = history["changes"][0]
    assert (change["field"], change["old_value"], change["new_value"]) == ("deadline", "2026-11-15", "2026-11-20")
    assert change["reason"] == "Extra security testing needed"
    assert change["source_title"] == "Meeting 3: Schedule Adjustment"

    # Asking via the old version returns the same full chain.
    assert get(client, f"/commitments/{first.id}/changes", company).json()["versions_count"] == 2


def test_decision_changes_endpoint(db, client):
    company, project, source = seed_company(db)
    old = add_memory(db, company, project, source, "Use Stripe", memory_type=MemoryType.DECISION)
    add_memory(db, company, project, source, "Use Stripe and PayPal", memory_type=MemoryType.DECISION,
               previous=old.id, reason="Client wants PayPal too")
    add_memory(db, company, project, source, "Use Next.js", memory_type=MemoryType.DECISION)  # never revised

    changes = get(client, "/decision-changes", company).json()
    assert len(changes) == 1
    assert changes[0]["current"]["title"] == "Use Stripe and PayPal"
    assert [v["title"] for v in changes[0]["previous_versions"]] == ["Use Stripe"]
    assert changes[0]["last_change_reason"] == "Client wants PayPal too"


# -------------------------------------------------------------
# Reminders
# -------------------------------------------------------------
def test_reminders_endpoint(db, client):
    company, project, source = seed_company(db)
    add_memory(db, company, project, source, "Send budget estimate", person="Aman", deadline="28 October 2026")
    add_memory(db, company, project, source, "Share revised proposal", person="Riya", deadline="2 November 2026")
    add_memory(db, company, project, source, "Complete the project", person="Srajan", deadline="30 November 2026")

    reminders = get(client, "/reminders", company, as_of=AS_OF).json()
    assert [r["severity"] for r in reminders] == ["overdue", "due_soon"]
    assert reminders[0]["message"] == "OVERDUE by 3 days: Aman - Send budget estimate (was due 28 Oct 2026)"
    assert reminders[1]["message"] == "DUE in 2 days: Riya - Share revised proposal (02 Nov 2026)"


# -------------------------------------------------------------
# Completing commitments
# -------------------------------------------------------------
def test_complete_commitment_flow(db, client):
    company, project, source = seed_company(db)
    task = add_memory(db, company, project, source, "Send budget estimate", person="Aman", deadline="28 October 2026")

    done = client.post(
        f"/api/tracker/commitments/{task.id}/complete",
        params={"as_of": AS_OF},
        json={"company_id": company.id, "note": "Sent by email"},
    )
    assert done.status_code == 200
    assert done.json()["tracker_status"] == "completed"
    assert done.json()["memory_status"] == "completed"

    assert get(client, "/overdue", company, as_of=AS_OF).json() == []
    assert get(client, "/summary", company, as_of=AS_OF).json()["completed"] == 1
    assert get(client, "/commitments", company, as_of=AS_OF, include_completed=False).json() == []
    assert len(get(client, "/commitments", company, as_of=AS_OF, status="completed").json()) == 1

    # Module 3 still sees the same memory, now with its completion details.
    stored = client.get(f"/api/memories/{task.id}", params={"company_id": company.id}).json()
    assert stored["status"] == "completed"
    assert stored["meta_info"]["completion_note"] == "Sent by email"
    assert stored["meta_info"]["person"] == "Aman"  # existing details preserved

    # Completing again is harmless.
    again = client.post(f"/api/tracker/commitments/{task.id}/complete", json={"company_id": company.id})
    assert again.status_code == 200


def test_cannot_complete_superseded_or_non_commitment(db, client):
    company, project, source = seed_company(db)
    first = add_memory(db, company, project, source, "Complete the project", person="Srajan", deadline="15 November 2026")
    add_memory(db, company, project, source, "Complete the project", person="Srajan",
               deadline="20 November 2026", previous=first.id)
    decision = add_memory(db, company, project, source, "Use Stripe", memory_type=MemoryType.DECISION)

    superseded = client.post(f"/api/tracker/commitments/{first.id}/complete", json={"company_id": company.id})
    assert superseded.status_code == 409
    not_commitment = client.post(f"/api/tracker/commitments/{decision.id}/complete", json={"company_id": company.id})
    assert not_commitment.status_code == 404


# -------------------------------------------------------------
# Tenant isolation and validation
# -------------------------------------------------------------
def test_company_isolation(db, client):
    company_a, project_a, source_a = seed_company(db, "Company A")
    company_b, _, _ = seed_company(db, "Company B")
    task = add_memory(db, company_a, project_a, source_a, "Secret task", person="Aman", deadline="28 October 2026")

    assert get(client, "/commitments", company_b, as_of=AS_OF).json() == []
    assert get(client, "/overdue", company_b, as_of=AS_OF).json() == []
    assert get(client, "/reminders", company_b, as_of=AS_OF).json() == []
    assert get(client, f"/commitments/{task.id}/changes", company_b).status_code == 404
    hijack = client.post(f"/api/tracker/commitments/{task.id}/complete", json={"company_id": company_b.id})
    assert hijack.status_code == 404
    assert get(client, "/overdue", company_a, as_of=AS_OF).json()[0]["title"] == "Secret task"  # untouched


def test_input_validation(client):
    assert client.get("/api/tracker/commitments").status_code == 422                       # company_id required
    assert client.get("/api/tracker/commitments", params={"company_id": ""}).status_code == 422
    assert client.get("/api/tracker/summary", params={"company_id": "x", "as_of": "not-a-date"}).status_code == 422
    assert client.get("/api/tracker/upcoming", params={"company_id": "x", "within_days": -1}).status_code == 422
    assert client.get("/api/tracker/commitments", params={"company_id": "x", "status": "bogus"}).status_code == 422
    assert client.post("/api/tracker/commitments/abc/complete", json={}).status_code == 422
    assert client.get("/api/tracker/commitments/missing/changes", params={"company_id": "x"}).status_code == 404


# -------------------------------------------------------------
# End to end: Module 2 payload -> Module 3 API -> Module 4
# -------------------------------------------------------------
def test_module2_payload_flows_through_module3_into_tracker(db, client):
    from memory_extraction.schemas import ExtractedMemory, ExtractionRequest

    company, project, source = seed_company(db)
    request = ExtractionRequest(
        company_id=company.id, source_id=source.id, project_id=project.id,
        extracted_text="Srajan will complete the project by 15 November.",
    )
    extracted = ExtractedMemory(
        memory_type="employee_commitment", title="Complete the project",
        content="Srajan will complete the project by 15 November.",
        person="Srajan", deadline="15 November 2026", confidence=0.92,
    )
    created = client.post("/api/memories/", json=extracted.to_memory_create_payload(request))
    assert created.status_code == 201

    row = get(client, "/commitments", company, as_of=AS_OF).json()[0]
    assert row["owner"] == "Srajan"
    assert row["deadline"] == "2026-11-15"
    assert row["tracker_status"] == "pending"
