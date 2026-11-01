import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from memory_extraction.routes import router as extraction_router
from memory_extraction.extractor import memory_extractor, MemoryExtractor
from memory_extraction.config import settings
from memory_engine.routes import router as memory_router
from memory_engine.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(extraction_router)
    return TestClient(app)


def test_extraction_health_endpoint(client):
    res = client.get("/api/extraction/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["module"] == "Module 2: Intelligent Memory Extraction"
    assert "provider" in data
    assert "provider_configured" in data


def test_extraction_unconfigured_provider(monkeypatch, client):
    # Without API keys configured, extraction should return 503
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(memory_extractor.llm_client, "_provider", None)
    res = client.post("/api/extraction/extract", json={
        "company_id": "comp-123",
        "source_id": "src-123",
        "extracted_text": "Meeting held to finalize roadmap."
    })
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


def test_extraction_blank_input_returns_422(client):
    res = client.post("/api/extraction/extract", json={
        "company_id": "comp-123",
        "source_id": "src-123",
        "extracted_text": "   "
    })
    assert res.status_code == 422


def test_extraction_too_large_returns_413(client):
    original_limit = settings.max_input_characters
    try:
        settings.max_input_characters = 20
        res = client.post("/api/extraction/extract", json={
            "company_id": "comp-123",
            "source_id": "src-123",
            "extracted_text": "This input text definitely exceeds twenty characters."
        })
        assert res.status_code == 413
    finally:
        settings.max_input_characters = original_limit


def test_extraction_success_with_mocked_llm(monkeypatch, client):
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "memories": [
            {
                "memory_type": "decision",
                "title": "Migrate database to PostgreSQL",
                "content": "The engineering team decided to migrate SQLite to PostgreSQL.",
                "confidence": 0.95,
                "tags": ["database", "postgres"],
                "entities": [{"entity_type": "other", "name": "PostgreSQL"}],
                "meta_info": {}
            }
        ],
        "entities": [{"entity_type": "other", "name": "PostgreSQL"}]
    }

    monkeypatch.setattr(memory_extractor, "llm_client", mock_llm)

    res = client.post("/api/extraction/extract", json={
        "company_id": "comp-100",
        "source_id": "src-100",
        "extracted_text": "We decided to migrate SQLite to PostgreSQL.",
        "filename": "infra_meeting.txt",
        "source_type": "meeting"
    })

    assert res.status_code == 200
    data = res.json()
    assert data["memories_count"] == 1
    assert data["memories"][0]["title"] == "Migrate database to PostgreSQL"
    assert len(data["module3_payloads"]) == 1
    assert data["module3_payloads"][0]["company_id"] == "comp-100"
    assert data["module3_payloads"][0]["source_id"] == "src-100"


def test_end_to_end_module2_to_module3_integration(monkeypatch):
    """Verifies that Module 2 extraction payloads cleanly ingest into Module 3 memory engine."""
    # Setup in-memory DB for Module 3
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db_session = TestingSessionLocal()

    app = FastAPI()
    app.include_router(extraction_router)
    app.include_router(memory_router)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # 1. Setup Company and Source in Module 3
    comp_res = client.post("/api/companies/", json={"name": "End2End Corp", "domain": "e2e.corp"})
    assert comp_res.status_code == 201
    comp_id = comp_res.json()["id"]

    src_res = client.post("/api/sources/", json={
        "company_id": comp_id,
        "title": "Kickoff Meeting",
        "source_type": "meeting",
        "raw_content": "Priya confirmed deployment of auth service by Friday."
    })
    assert src_res.status_code == 201
    src_id = src_res.json()["id"]

    # 2. Extract using Module 2 (mocked LLM)
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "memories": [
            {
                "memory_type": "employee_commitment",
                "title": "Auth Service Deployment",
                "content": "Priya confirmed deployment of auth service by Friday.",
                "person": "Priya",
                "deadline": "Friday",
                "confidence": 0.95,
                "tags": ["deployment", "auth"],
                "entities": [{"entity_type": "person", "name": "Priya"}],
                "meta_info": {"service": "auth"}
            }
        ],
        "entities": [{"entity_type": "person", "name": "Priya"}]
    }
    monkeypatch.setattr(memory_extractor, "llm_client", mock_llm)

    ext_res = client.post("/api/extraction/extract", json={
        "company_id": comp_id,
        "source_id": src_id,
        "extracted_text": "Priya confirmed deployment of auth service by Friday."
    })
    assert ext_res.status_code == 200
    payloads = ext_res.json()["module3_payloads"]
    assert len(payloads) == 1

    # 3. Ingest into Module 3 Memory Engine using the payload from Module 2
    mem_res = client.post("/api/memories/", json=payloads[0])
    assert mem_res.status_code == 201
    created_mem = mem_res.json()
    assert created_mem["title"] == "Auth Service Deployment"
    assert created_mem["memory_type"] == "employee_commitment"

    # 4. Search via Semantic Search
    search_res = client.post("/api/search/", json={
        "company_id": comp_id,
        "query": "When is Priya deploying auth service?"
    })
    assert search_res.status_code == 200
    assert search_res.json()["results_count"] >= 1

    # 5. RAG Chat
    chat_res = client.post("/api/chat/", json={
        "company_id": comp_id,
        "question": "What is the status of the auth service deployment?"
    })
    assert chat_res.status_code == 200
    db_session.close()
    Base.metadata.drop_all(bind=test_engine)


def test_extract_and_store_endpoint(monkeypatch):
    """Verifies that /api/extraction/extract-and-store successfully stores memories and returns source_summary without error."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db_session = TestingSessionLocal()

    app = FastAPI()
    app.include_router(extraction_router)
    app.include_router(memory_router)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "source_summary": "Architecture board approved PostgreSQL with pgvector.",
        "memories": [
            {
                "memory_type": "decision",
                "title": "Use PostgreSQL with pgvector",
                "content": "The team decided to use PostgreSQL with pgvector for production.",
                "confidence": 0.98,
                "tags": ["postgres", "vector"],
                "entities": [{"entity_type": "other", "name": "PostgreSQL"}],
                "meta_info": {}
            }
        ],
        "entities": [{"entity_type": "other", "name": "PostgreSQL"}]
    }
    monkeypatch.setattr(memory_extractor, "llm_client", mock_llm)

    res = client.post("/api/extraction/extract-and-store", json={
        "company_id": "default-org",
        "title": "Executive Board Meeting",
        "text": "The team decided to use PostgreSQL with pgvector for production."
    })

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["stored_count"] == 1
    assert "source_id" in data
    assert "source_summary" in data
    assert "extraction_summary" in data
    assert "PostgreSQL" in data["source_summary"]
    assert len(data["memories"]) == 1

    db_session.close()
    Base.metadata.drop_all(bind=test_engine)
