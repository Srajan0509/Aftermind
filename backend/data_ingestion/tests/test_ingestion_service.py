import io
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from memory_engine.database import Base
from memory_engine.models import Source
from memory_engine.schemas import CompanyCreate
from memory_engine.memory_service import memory_service
from data_ingestion.config import ingestion_settings
from data_ingestion.service import ingestion_service
from data_ingestion.schemas import TextIngestRequest, IngestionSourceType
from data_ingestion.tests.test_parsers import make_pdf_with_fitz


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


# -------------------------------------------------------------------
# Standalone Ingestion Tests (No Database / Optional Module 3)
# -------------------------------------------------------------------
def test_standalone_text_ingestion_without_database():
    """Verifies Module 1 operates completely independently without requiring a DB."""
    req = TextIngestRequest(
        title="Quick Standalone Note",
        text="The team decided to launch the MVP on December 20, 2026.",
        source_type=IngestionSourceType.DOCUMENT,
        trigger_extraction=False
    )
    res = ingestion_service.ingest_text(req, db=None)

    assert res.source_id is not None
    assert res.source_id.startswith("standalone-")
    assert res.persisted_to_storage is False
    assert "launch the MVP on December 20" in res.extracted_text
    assert res.word_count > 0


def test_standalone_document_ingestion_without_database():
    """Verifies document parsing works independently with zero DB setup."""
    pdf_bytes = make_pdf_with_fitz("Client agreed to standard SLA terms.")
    res = ingestion_service.ingest_document(
        content=pdf_bytes,
        filename="sla.pdf",
        db=None,
        trigger_extraction=False
    )

    assert res.source_id.startswith("standalone-")
    assert res.persisted_to_storage is False
    assert "Client agreed to standard SLA terms" in res.extracted_text
    assert res.metadata["file_type"] == "pdf"


# -------------------------------------------------------------------
# Integrated Ingestion Tests (With Module 3 Database Persistence)
# -------------------------------------------------------------------
def test_ingest_text_persists_in_module3(db):
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Acme Ingestion Corp"))

    req = TextIngestRequest(
        company_id=comp.id,
        title="Strategy Call Transcript",
        text="We decided to use FastAPI for our business memory API. Target delivery is Q4.",
        source_type=IngestionSourceType.MEETING,
        trigger_extraction=False
    )
    res = ingestion_service.ingest_text(req, db=db)

    assert res.source_id is not None
    assert not res.source_id.startswith("standalone-")
    assert res.persisted_to_storage is True
    assert res.company_id == comp.id

    db_source = db.query(Source).filter(Source.id == res.source_id).first()
    assert db_source is not None
    assert db_source.title == "Strategy Call Transcript"
    assert db_source.source_type == "meeting"
    assert "FastAPI for our business memory API" in db_source.raw_content


def test_ingest_document_persists_in_module3(db):
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Doc Ingestion Corp"))
    pdf_bytes = make_pdf_with_fitz("Product specification for Cloud Storage Migration.")

    res = ingestion_service.ingest_document(
        content=pdf_bytes,
        filename="spec.pdf",
        company_id=comp.id,
        db=db,
        title="Product Spec",
        source_type=IngestionSourceType.DOCUMENT,
        trigger_extraction=False
    )

    assert res.source_id is not None
    assert res.persisted_to_storage is True

    db_source = db.query(Source).filter(Source.id == res.source_id).first()
    assert db_source is not None
    assert db_source.meta_info["file_type"] == "pdf"


def test_ingest_audio_persists_in_module3(db):
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Voice Ingestion Corp"))
    valid_mp3 = b"ID3\x03\x00\x00\x00\x00\x00#DUMMY_MP3_STREAM_PAYLOAD_DATA"

    res = ingestion_service.ingest_audio(
        audio_bytes=valid_mp3,
        filename="team_call.mp3",
        company_id=comp.id,
        db=db,
        title="Team Standup Call",
        source_type=IngestionSourceType.MEETING,
        trigger_extraction=False
    )

    assert res.source_id is not None
    assert res.persisted_to_storage is True
    assert res.source_type == "meeting"

    db_source = db.query(Source).filter(Source.id == res.source_id).first()
    assert db_source is not None
    assert db_source.source_type == "meeting"


def test_ingest_rejects_nonexistent_company(db):
    req = TextIngestRequest(
        company_id="non-existent-company-uuid-00000",
        title="Orphan Note",
        text="This should fail validation because the company does not exist in the database.",
        trigger_extraction=False
    )
    with pytest.raises(ValueError) as exc_info:
        ingestion_service.ingest_text(req, db=db)
    assert "does not exist" in str(exc_info.value)
