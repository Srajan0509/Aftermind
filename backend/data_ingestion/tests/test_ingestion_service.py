import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from memory_engine.database import Base
from memory_engine.models import Company, Source
from memory_engine.schemas import CompanyCreate
from memory_engine.memory_service import memory_service
from data_ingestion.service import ingestion_service
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


def test_ingest_text_persists_in_module3(db):
    # 1. Setup Company in Module 3
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Acme Ingestion Corp"))

    # 2. Ingest text
    req = TextIngestRequest(
        company_id=comp.id,
        title="Strategy Call Transcript",
        text="We decided to use FastAPI for our business memory API. Target delivery is Q4.",
        source_type=IngestionSourceType.MEETING,
        trigger_extraction=False
    )
    res = ingestion_service.ingest_text(req, db=db)

    assert res.source_id is not None
    assert res.company_id == comp.id
    assert res.title == "Strategy Call Transcript"
    assert res.source_type == "meeting"
    assert res.word_count > 0

    # 3. Verify in database
    db_source = db.query(Source).filter(Source.id == res.source_id).first()
    assert db_source is not None
    assert db_source.title == "Strategy Call Transcript"
    assert db_source.source_type == "meeting"
    assert "FastAPI for our business memory API" in db_source.raw_content


def test_ingest_document_persists_in_module3(db):
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Document Testing Corp"))
    md_content = b"# Product Requirements\n\nClient requires single sign-on via SAML."

    res = ingestion_service.ingest_document(
        content=md_content,
        filename="PRD.md",
        company_id=comp.id,
        db=db,
        title="Product Requirements Document",
        source_type=IngestionSourceType.DOCUMENT,
        trigger_extraction=False
    )

    assert res.source_id is not None
    assert res.title == "Product Requirements Document"
    assert "Client requires single sign-on" in res.extracted_text

    db_source = db.query(Source).filter(Source.id == res.source_id).first()
    assert db_source is not None
    assert db_source.meta_info["file_type"] == "md"


def test_ingest_audio_persists_in_module3(db):
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Voice Audio Corp"))
    audio_content = b"DUMMY_MP3_AUDIO_STREAM_FOR_VOICE_NOTE"

    res = ingestion_service.ingest_audio(
        audio_bytes=audio_content,
        filename="founder_note.mp3",
        company_id=comp.id,
        db=db,
        title="Founder Voice Memo",
        source_type=IngestionSourceType.VOICE_NOTE,
        trigger_extraction=False
    )

    assert res.source_id is not None
    assert res.source_type == "voice_note"
    assert len(res.extracted_text) > 0

    db_source = db.query(Source).filter(Source.id == res.source_id).first()
    assert db_source is not None
    assert db_source.source_type == "voice_note"


def test_ingest_rejects_nonexistent_company(db):
    req = TextIngestRequest(
        company_id="non-existent-company-uuid-12345",
        title="Orphan Note",
        text="This should fail validation because the company does not exist.",
        trigger_extraction=False
    )
    with pytest.raises(ValueError) as exc_info:
        ingestion_service.ingest_text(req, db=db)
    assert "does not exist" in str(exc_info.value)
