import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from memory_engine.database import Base
from memory_engine.schemas import CompanyCreate
from memory_engine.memory_service import memory_service
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
    assert ".pdf" in resp.supported_document_types
    assert ".docx" in resp.supported_document_types
    assert ".mp3" in resp.supported_audio_types
    assert resp.max_input_characters == 100000


def test_text_endpoint(db):
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
    assert res.title == "Weekly Sync Call"
    assert res.character_count > 0


def test_pipeline_endpoint(db):
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Pipeline Route Testing"))
    req = TextIngestRequest(
        company_id=comp.id,
        title="Pipeline Document",
        text="The client requires two-factor authentication via SMS or authenticator app.",
        source_type=IngestionSourceType.DOCUMENT,
        trigger_extraction=False
    )
    res = ingest_pipeline_endpoint(req, db=db)
    assert res.source_id is not None
    assert res.status == "completed"


def test_text_endpoint_rejects_empty(db):
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Error Route Testing"))
    # Pydantic validation rejects blank text
    with pytest.raises(Exception):
        TextIngestRequest(
            company_id=comp.id,
            title="Empty Note",
            text="   ",
            trigger_extraction=False
        )
