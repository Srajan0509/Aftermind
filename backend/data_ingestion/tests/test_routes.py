import io
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from memory_engine.database import Base
from memory_engine.schemas import CompanyCreate
from memory_engine.memory_service import memory_service
from data_ingestion.config import ingestion_settings
from data_ingestion.routes import (
    ingest_text_endpoint,
    ingest_pipeline_endpoint,
    ingestion_health_endpoint,
)
from data_ingestion.schemas import TextIngestRequest, IngestionSourceType


TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
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


def test_health_endpoint():
    resp = ingestion_health_endpoint()
    assert resp.status == "healthy"
    assert "Module 1" in resp.module
    # Exactly 3 document formats and 3 audio formats
    assert resp.supported_document_types == [".docx", ".pdf", ".txt"]
    assert resp.supported_audio_types == [".m4a", ".mp3", ".wav"]
    assert resp.max_input_characters == 100000


def test_text_endpoint_standalone():
    """Text endpoint executes cleanly in standalone mode without a company_id or db."""
    req = TextIngestRequest(
        title="Quick Standalone Memo",
        text="Target completion date for Stripe payment integration is November 30.",
        source_type=IngestionSourceType.DOCUMENT,
        trigger_extraction=False
    )
    res = ingest_text_endpoint(req, db=None)
    assert res.source_id is not None
    assert res.persisted_to_storage is False
    assert res.character_count > 0


def test_text_endpoint_with_db(db):
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Route Testing Inc"))
    req = TextIngestRequest(
        company_id=comp.id,
        title="Weekly Sync Call",
        text="Discussed launch schedule. We will deploy the payment processor by Friday.",
        source_type=IngestionSourceType.MEETING,
        trigger_extraction=False
    )
    res = ingest_text_endpoint(req, db=db)
    assert res.source_id is not None
    assert res.persisted_to_storage is True
    assert res.title == "Weekly Sync Call"


def test_pipeline_endpoint_standalone():
    req = TextIngestRequest(
        title="Pipeline Document",
        text="The client requires two-factor authentication via SMS or authenticator app.",
        source_type=IngestionSourceType.DOCUMENT,
        trigger_extraction=False
    )
    res = ingest_pipeline_endpoint(req, db=None)
    assert res.source_id is not None
    assert res.status == "completed"


def test_text_endpoint_rejects_empty():
    with pytest.raises(Exception):
        TextIngestRequest(
            title="Empty Note",
            text="   ",
            trigger_extraction=False
        )
