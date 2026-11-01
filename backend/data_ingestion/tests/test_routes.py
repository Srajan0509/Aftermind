import io
import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from memory_engine.database import Base
from memory_engine.schemas import CompanyCreate
from memory_engine.memory_service import memory_service
from data_ingestion.config import ingestion_settings
from data_ingestion.routes import (
    ingest_text_endpoint,
    ingest_document_endpoint,
    ingest_audio_endpoint,
    ingest_pipeline_endpoint,
    ingestion_health_endpoint,
)
from data_ingestion.schemas import TextIngestRequest, IngestionSourceType
from data_ingestion.tests.test_parsers import make_pdf_with_fitz, make_docx_with_metadata


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
# 1. Health Endpoint Tests
# -------------------------------------------------------------------
def test_health_endpoint():
    resp = ingestion_health_endpoint()
    assert resp.status == "healthy"
    assert "Module 1" in resp.module
    assert resp.supported_document_types == [".docx", ".pdf", ".txt"]
    assert resp.supported_audio_types == [".m4a", ".mp3", ".wav"]
    assert resp.max_input_characters == 100000


# -------------------------------------------------------------------
# 2. Text & Pipeline Endpoint Tests
# -------------------------------------------------------------------
def test_text_endpoint_standalone():
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


# -------------------------------------------------------------------
# 3. Document Upload Endpoint Tests (PDF, DOCX, TXT)
# -------------------------------------------------------------------
def test_document_endpoint_pdf_upload():
    pdf_bytes = make_pdf_with_fitz("Client requirements for cloud migration approved.")
    file = UploadFile(filename="migration.pdf", file=io.BytesIO(pdf_bytes))
    res = ingest_document_endpoint(file=file, db=None, trigger_extraction=False)

    assert res.source_id is not None
    assert "requirements for cloud migration" in res.extracted_text
    assert res.metadata["file_type"] == "pdf"


def test_document_endpoint_docx_upload():
    docx_bytes = make_docx_with_metadata("Meeting concluded with deadline set to Dec 15.")
    file = UploadFile(filename="meeting.docx", file=io.BytesIO(docx_bytes))
    res = ingest_document_endpoint(file=file, db=None, trigger_extraction=False)

    assert res.source_id is not None
    assert "deadline set to Dec 15" in res.extracted_text
    assert res.metadata["file_type"] == "docx"


def test_document_endpoint_txt_upload():
    txt_bytes = b"Discussion on payment gateway architecture: Stripe chosen."
    file = UploadFile(filename="payment.txt", file=io.BytesIO(txt_bytes))
    res = ingest_document_endpoint(file=file, db=None, trigger_extraction=False)

    assert res.source_id is not None
    assert "Stripe chosen" in res.extracted_text
    assert res.metadata["file_type"] == "txt"


def test_document_endpoint_rejects_empty_file():
    empty_file = UploadFile(filename="blank.txt", file=io.BytesIO(b""))
    with pytest.raises(HTTPException) as exc_info:
        ingest_document_endpoint(file=empty_file, db=None)
    assert exc_info.value.status_code == 422
    assert "empty" in exc_info.value.detail.lower()


def test_document_endpoint_rejects_missing_filename():
    unnamed_file = UploadFile(filename="", file=io.BytesIO(b"Some text"))
    with pytest.raises(HTTPException) as exc_info:
        ingest_document_endpoint(file=unnamed_file, db=None)
    assert exc_info.value.status_code == 400


def test_document_endpoint_rejects_unsupported_format():
    exe_file = UploadFile(filename="binary.exe", file=io.BytesIO(b"Binary content"))
    with pytest.raises(HTTPException) as exc_info:
        ingest_document_endpoint(file=exe_file, db=None)
    assert exc_info.value.status_code == 422
    assert "unsupported document format" in exc_info.value.detail.lower()


def test_document_endpoint_rejects_mime_mismatch():
    fake_pdf = UploadFile(filename="spoofed.pdf", file=io.BytesIO(b"Plain text not PDF"))
    with pytest.raises(HTTPException) as exc_info:
        ingest_document_endpoint(file=fake_pdf, db=None)
    assert exc_info.value.status_code == 422
    assert "mime/format mismatch" in exc_info.value.detail.lower()


def test_document_endpoint_with_db_persistence(db):
    comp = memory_service.get_or_create_company(db, CompanyCreate(name="Doc Upload Corp"))
    pdf_bytes = make_pdf_with_fitz("Persisted document in company memory.")
    file = UploadFile(filename="contract.pdf", file=io.BytesIO(pdf_bytes))
    res = ingest_document_endpoint(file=file, company_id=comp.id, db=db, trigger_extraction=False)

    assert res.source_id is not None
    assert res.persisted_to_storage is True
    assert res.company_id == comp.id


# -------------------------------------------------------------------
# 4. Audio Upload Endpoint Tests (MP3, WAV, M4A)
# -------------------------------------------------------------------
def test_audio_endpoint_valid_upload():
    ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = True
    valid_mp3 = b"ID3\x03\x00\x00\x00\x00\x00#DUMMY_MP3_STREAM_PAYLOAD_DATA"
    file = UploadFile(filename="voice.mp3", file=io.BytesIO(valid_mp3))
    res = ingest_audio_endpoint(file=file, db=None, trigger_extraction=False)

    assert res.source_id is not None
    assert len(res.extracted_text) > 0
    assert res.metadata["audio_format"] == "mp3"


def test_audio_endpoint_rejects_empty():
    empty_file = UploadFile(filename="silent.wav", file=io.BytesIO(b""))
    with pytest.raises(HTTPException) as exc_info:
        ingest_audio_endpoint(file=empty_file, db=None)
    assert exc_info.value.status_code == 422
    assert "empty" in exc_info.value.detail.lower()


def test_audio_endpoint_rejects_mime_mismatch():
    fake_wav = UploadFile(filename="fake.wav", file=io.BytesIO(b"Not a RIFF header"))
    with pytest.raises(HTTPException) as exc_info:
        ingest_audio_endpoint(file=fake_wav, db=None)
    assert exc_info.value.status_code == 422
    assert "mime/format mismatch" in exc_info.value.detail.lower()


def test_audio_endpoint_missing_credentials_returns_503():
    """Verifies that missing credentials in production return HTTP 503 Service Unavailable."""
    saved_mock = ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER
    saved_openai = ingestion_settings.OPENAI_API_KEY
    saved_gemini = ingestion_settings.GEMINI_API_KEY

    try:
        ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = False
        ingestion_settings.OPENAI_API_KEY = ""
        ingestion_settings.GEMINI_API_KEY = ""

        valid_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00"
        file = UploadFile(filename="recording.wav", file=io.BytesIO(valid_wav))

        with pytest.raises(HTTPException) as exc_info:
            ingest_audio_endpoint(file=file, db=None)

        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail.lower()
    finally:
        ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER = saved_mock
        ingestion_settings.OPENAI_API_KEY = saved_openai
        ingestion_settings.GEMINI_API_KEY = saved_gemini
