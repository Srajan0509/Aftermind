import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from memory_engine.database import Base, get_db
from memory_engine.routes import router
from memory_engine.schemas import (
    CompanyCreate,
    ProjectCreate,
    PersonCreate,
    SourceCreate,
    SourceType,
    MemoryCreate,
    MemoryType,
    MemoryStatus,
    RelationshipType
)
from memory_engine.memory_service import memory_service
from memory_engine.relationship_service import relationship_service
from memory_engine.vector_search import vector_search_engine
from memory_engine.rag_engine import rag_engine
from memory_engine.schemas import RAGChatRequest, SemanticSearchRequest
from fastapi import FastAPI


# Setup test database
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """Provides a clean in-memory database session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """Provides a TestClient with dependency override for get_db."""
    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(test_app) as c:
        yield c


# -------------------------------------------------------------
# 1. Embedding Generation Tests
# -------------------------------------------------------------
def test_embedding_generation():
    from memory_engine.embedding_service import embedding_service
    vec1 = embedding_service.generate_embedding("payment gateway integration with Stripe")
    vec2 = embedding_service.generate_embedding("payment gateway setup and processing")
    vec3 = embedding_service.generate_embedding("catering lunch menu options")

    assert len(vec1) == 1536
    assert len(vec2) == 1536
    assert len(vec3) == 1536

    # Payment queries should be more similar to each other than to lunch catering
    sim_related = embedding_service.cosine_similarity(vec1, vec2)
    sim_unrelated = embedding_service.cosine_similarity(vec1, vec3)

    assert sim_related > sim_unrelated


# -------------------------------------------------------------
# 2. Memory Ingestion & Source Preservation
# -------------------------------------------------------------
def test_memory_insertion_and_source_traceability(db):
    company = memory_service.get_or_create_company(db, CompanyCreate(name="Acme Corp", domain="acme.com"))
    project = memory_service.get_or_create_project(db, ProjectCreate(company_id=company.id, name="Cloud Migration"))
    person = memory_service.get_or_create_person(db, PersonCreate(company_id=company.id, name="Alice Chen", role="CTO"))

    source = memory_service.create_source(db, SourceCreate(
        company_id=company.id,
        project_id=project.id,
        author_id=person.id,
        title="Architecture Review Meeting #1",
        source_type=SourceType.MEETING,
        raw_content="Alice Chen confirmed we will migrate all Postgres databases to AWS RDS by Q3."
    ))

    memory = memory_service.create_memory(db, MemoryCreate(
        company_id=company.id,
        project_id=project.id,
        source_id=source.id,
        author_id=person.id,
        memory_type=MemoryType.DECISION,
        title="PostgreSQL Migration Target",
        content="Migrate all production Postgres databases to AWS RDS.",
        tags=["database", "cloud"]
    ))

    assert memory.id is not None
    assert memory.company_id == company.id
    assert memory.source_id == source.id
    assert memory.source_title == "Architecture Review Meeting #1"
    assert memory.source_type == "meeting"
    assert memory.project_name == "Cloud Migration"


# -------------------------------------------------------------
# 3. Persistent Memory Across Multiple Meetings (Example Scenario)
# -------------------------------------------------------------
def test_multiple_meeting_persistence_and_timeline(db):
    """
    Simulates the exact example scenario:
    Meeting 1: ABC Technologies requested website development.
    Meeting 2: ABC Technologies requested payment gateway integration.
    Meeting 3: ABC Technologies changed the project deadline.
    """
    company = memory_service.get_or_create_company(db, CompanyCreate(name="ABC Technologies", domain="abctech.com"))
    project = memory_service.get_or_create_project(db, ProjectCreate(company_id=company.id, name="E-Commerce Revamp"))

    # Meeting 1
    m1_source = memory_service.create_source(db, SourceCreate(
        company_id=company.id,
        project_id=project.id,
        title="Meeting 1: Project Kickoff",
        source_type=SourceType.MEETING,
        raw_content="ABC Technologies requested full-stack website development with Next.js."
    ))
    mem1 = memory_service.create_memory(db, MemoryCreate(
        company_id=company.id,
        project_id=project.id,
        source_id=m1_source.id,
        memory_type=MemoryType.CLIENT_REQUIREMENT,
        title="Website Development Scope",
        content="ABC Technologies requested complete modern website development using Next.js."
    ))

    # Initial deadline decision from Meeting 1
    initial_deadline_mem = memory_service.create_memory(db, MemoryCreate(
        company_id=company.id,
        project_id=project.id,
        source_id=m1_source.id,
        memory_type=MemoryType.IMPORTANT_DEADLINE,
        title="Initial Project Launch Deadline",
        content="Target completion date agreed as November 30, 2026."
    ))

    # Meeting 2
    m2_source = memory_service.create_source(db, SourceCreate(
        company_id=company.id,
        project_id=project.id,
        title="Meeting 2: Payment Integration",
        source_type=SourceType.MEETING,
        raw_content="ABC Technologies requested payment gateway integration using Stripe and PayPal."
    ))
    mem2 = memory_service.create_memory(db, MemoryCreate(
        company_id=company.id,
        project_id=project.id,
        source_id=m2_source.id,
        memory_type=MemoryType.CLIENT_REQUIREMENT,
        title="Payment Gateway Integration",
        content="ABC Technologies requested payment gateway integration with Stripe and PayPal."
    ))

    # Meeting 3: Deadline Change (Supersedes initial deadline)
    m3_source = memory_service.create_source(db, SourceCreate(
        company_id=company.id,
        project_id=project.id,
        title="Meeting 3: Scope & Schedule Adjustment",
        source_type=SourceType.MEETING,
        raw_content="Due to payment gateway compliance, ABC Technologies postponed the deadline to December 20, 2026."
    ))
    mem3_updated_deadline = memory_service.create_memory(db, MemoryCreate(
        company_id=company.id,
        project_id=project.id,
        source_id=m3_source.id,
        memory_type=MemoryType.IMPORTANT_DEADLINE,
        title="Extended Project Launch Deadline",
        content="Project launch deadline rescheduled to December 20, 2026.",
        previous_memory_id=initial_deadline_mem.id,
        change_reason="Additional security testing needed for payment gateway."
    ))

    # Verification: All memories belong to ABC Technologies & E-Commerce Revamp
    all_company_mems = memory_service.get_company_memories(db, company.id)
    assert len(all_company_mems) == 4

    # Verification: Old deadline memory is now marked as SUPERSEDED
    old_deadline = memory_service.get_memory(db, initial_deadline_mem.id)
    assert old_deadline.status == MemoryStatus.SUPERSEDED.value

    # Verification: History chain traces the decision change
    history = memory_service.get_memory_history(db, mem3_updated_deadline.id)
    assert len(history.timeline) == 2
    assert history.timeline[0].id == initial_deadline_mem.id
    assert history.timeline[1].id == mem3_updated_deadline.id


# -------------------------------------------------------------
# 4. Semantic Search Tests
# -------------------------------------------------------------
def test_semantic_search(db):
    company = memory_service.get_or_create_company(db, CompanyCreate(name="Stripe Partner", domain="stripe.com"))
    source = memory_service.create_source(db, SourceCreate(
        company_id=company.id,
        title="Integration Call",
        raw_content="Discussed webhooks and refunds processing."
    ))

    memory_service.create_memory(db, MemoryCreate(
        company_id=company.id,
        source_id=source.id,
        memory_type=MemoryType.DECISION,
        title="Webhook Retry Policy",
        content="Implement exponential backoff for failed webhook deliveries."
    ))

    memory_service.create_memory(db, MemoryCreate(
        company_id=company.id,
        source_id=source.id,
        memory_type=MemoryType.CLIENT_REQUIREMENT,
        title="Refund Processing SLA",
        content="Process customer refund requests within 2 business days."
    ))

    # Natural language query
    results = vector_search_engine.search(
        db=db,
        query="What is our policy for webhook retries?",
        company_id=company.id,
        min_similarity=0.20
    )

    assert len(results) > 0
    assert "Webhook Retry Policy" in results[0].memory.title


# -------------------------------------------------------------
# 5. Multi-Tenant Data Isolation Test (Security)
# -------------------------------------------------------------
def test_company_data_isolation(db):
    """
    Crucial security test:
    Verify that Company B CANNOT access, retrieve, or search Company A's memories.
    """
    comp_a = memory_service.get_or_create_company(db, CompanyCreate(name="Company A Secret"))
    comp_b = memory_service.get_or_create_company(db, CompanyCreate(name="Company B Competitor"))

    source_a = memory_service.create_source(db, SourceCreate(
        company_id=comp_a.id,
        title="Confidential Strategy Session",
        raw_content="Company A is launching project Phoenix secretly."
    ))

    memory_service.create_memory(db, MemoryCreate(
        company_id=comp_a.id,
        source_id=source_a.id,
        memory_type=MemoryType.DECISION,
        title="Project Phoenix Budget",
        content="Approved $5,000,000 budget for project Phoenix."
    ))

    # Company B searches for Phoenix
    results_comp_b = vector_search_engine.search(
        db=db,
        query="project phoenix budget",
        company_id=comp_b.id,
        min_similarity=0.1
    )

    # Must return NOTHING for Company B
    assert len(results_comp_b) == 0

    # RAG query for Company B must state not found
    rag_resp_b = rag_engine.answer_question(db, RAGChatRequest(
        question="What is the budget for Project Phoenix?",
        company_id=comp_b.id
    ))
    assert rag_resp_b.is_grounded is False
    assert len(rag_resp_b.sources) == 0
    assert "could not find" in rag_resp_b.answer.lower()


# -------------------------------------------------------------
# 6. RAG Generation and Source Citing Tests
# -------------------------------------------------------------
def test_rag_generation_and_source_citations(db):
    company = memory_service.get_or_create_company(db, CompanyCreate(name="FinTech Solutions"))
    source = memory_service.create_source(db, SourceCreate(
        company_id=company.id,
        title="Sprint 14 Planning",
        source_type=SourceType.MEETING,
        raw_content="Meeting decided to deploy the PCI-DSS compliant payment gateway."
    ))

    memory_service.create_memory(db, MemoryCreate(
        company_id=company.id,
        source_id=source.id,
        memory_type=MemoryType.DECISION,
        title="PCI-DSS Compliance Decision",
        content="Payment gateway must strictly adhere to PCI-DSS Level 1 specifications."
    ))

    rag_req = RAGChatRequest(
        question="What was decided about payment gateway compliance?",
        company_id=company.id
    )

    rag_resp = rag_engine.answer_question(db, rag_req)

    assert rag_resp.is_grounded is True
    assert rag_resp.retrieved_memories_count >= 1
    assert len(rag_resp.sources) >= 1
    assert rag_resp.sources[0].source_title == "Sprint 14 Planning"
    assert "PCI-DSS" in rag_resp.answer


# -------------------------------------------------------------
# 7. FastAPI Endpoint Integration Tests via TestClient
# -------------------------------------------------------------
def test_api_endpoints(client):
    # 1. Create Company
    res = client.post("/api/companies/", json={"name": "Delta Logistics", "domain": "deltalog.com"})
    assert res.status_code == 201
    comp_id = res.json()["id"]

    # 2. Create Project
    res = client.post("/api/projects/", json={"company_id": comp_id, "name": "Fleet Tracking"})
    assert res.status_code == 201
    proj_id = res.json()["id"]

    # 3. Create Source
    res = client.post("/api/sources/", json={
        "company_id": comp_id,
        "project_id": proj_id,
        "title": "Vendor Selection Call",
        "source_type": "meeting",
        "raw_content": "We agreed to select GPS Provider X."
    })
    assert res.status_code == 201
    source_id = res.json()["id"]

    # 4. Ingest Memory
    res = client.post("/api/memories/", json={
        "company_id": comp_id,
        "project_id": proj_id,
        "source_id": source_id,
        "memory_type": "decision",
        "title": "GPS Vendor Decision",
        "content": "Selected GPS Provider X for fleet telematics."
    })
    assert res.status_code == 201
    mem_id = res.json()["id"]

    # 5. Semantic Search Endpoint
    res = client.post("/api/search/", json={
        "query": "Which GPS vendor did we select?",
        "company_id": comp_id
    })
    assert res.status_code == 200
    search_data = res.json()
    assert search_data["results_count"] >= 1
    assert search_data["results"][0]["memory"]["id"] == mem_id

    # 6. RAG Chat Endpoint
    res = client.post("/api/chat/", json={
        "question": "What is our GPS provider decision?",
        "company_id": comp_id
    })
    assert res.status_code == 200
    chat_data = res.json()
    assert chat_data["is_grounded"] is True
    assert len(chat_data["sources"]) >= 1
    assert chat_data["sources"][0]["source_title"] == "Vendor Selection Call"

    # 7. List Company Memories
    res = client.get(f"/api/companies/{comp_id}/memories")
    assert res.status_code == 200
    assert len(res.json()) >= 1
