import io
import json
import zipfile
import pytest

from data_ingestion.parsers.dispatcher import document_dispatcher
from data_ingestion.parsers.base import DocumentParsingError


def make_minimal_pdf(text: str) -> bytes:
    """Creates a valid, lightweight PDF file containing the specified text string."""
    stream_content = f"BT /F1 12 Tf 72 712 Td ({text}) Tj ET".encode("latin-1")
    stream_len = len(stream_content)
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>> endobj\n"
        b"4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"5 0 obj <</Length " + str(stream_len).encode("latin-1") + b">> stream\n" +
        stream_content +
        b"\nendstream\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"trailer <</Size 6 /Root 1 0 R>>\nstartxref\n500\n%%EOF"
    )
    return pdf


def make_minimal_docx(text: str) -> bytes:
    """Creates a valid, lightweight DOCX archive containing the specified text string."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>'
        )
        doc_xml = (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>'
            '</w:document>'
        )
        zf.writestr("word/document.xml", doc_xml)
    return buf.getvalue()


# -------------------------------------------------------------------
# Format 1: Plain Text (.txt)
# -------------------------------------------------------------------
def test_parse_valid_txt():
    content = b"Decision: We decided to deploy the service on AWS ECS.\nDeadline: November 15."
    res = document_dispatcher.parse_document(content, "meeting_notes.txt")
    assert res.file_type == "txt"
    assert "deploy the service on AWS ECS" in res.extracted_text
    assert res.word_count > 0


# -------------------------------------------------------------------
# Format 2: Markdown (.md)
# -------------------------------------------------------------------
def test_parse_valid_markdown():
    content = b"# Sprint Goals\n\n- Feature A: Complete authentication\n- Feature B: Build memory extraction"
    res = document_dispatcher.parse_document(content, "sprint.md")
    assert res.file_type == "md"
    assert "Complete authentication" in res.extracted_text
    assert res.metadata["format"] == "markdown"


# -------------------------------------------------------------------
# Format 3: CSV (.csv)
# -------------------------------------------------------------------
def test_parse_valid_csv():
    content = b"Task,Owner,Status\nDatabase Migration,Alice,Completed\nUI Redesign,Bob,In Progress"
    res = document_dispatcher.parse_document(content, "tracker.csv")
    assert res.file_type == "csv"
    assert "Task: Database Migration; Owner: Alice; Status: Completed" in res.extracted_text
    assert res.metadata["column_count"] == 3
    assert res.metadata["row_count"] == 2


# -------------------------------------------------------------------
# Format 4: JSON (.json)
# -------------------------------------------------------------------
def test_parse_valid_json():
    data = {
        "meeting_topic": "Architecture Review",
        "participants": ["Alice", "Bob"],
        "decisions": ["Adopt PostgreSQL with pgvector"]
    }
    content = json.dumps(data).encode("utf-8")
    res = document_dispatcher.parse_document(content, "meeting.json")
    assert res.file_type == "json"
    assert "meeting_topic: Architecture Review" in res.extracted_text
    assert "Adopt PostgreSQL with pgvector" in res.extracted_text


# -------------------------------------------------------------------
# Format 5: PDF (.pdf)
# -------------------------------------------------------------------
def test_parse_valid_pdf():
    pdf_bytes = make_minimal_pdf("Project Phoenix deadline is December 20.")
    res = document_dispatcher.parse_document(pdf_bytes, "proposal.pdf")
    assert res.file_type == "pdf"
    assert "Project Phoenix deadline is December 20" in res.extracted_text
    assert res.metadata["page_count"] >= 1


# -------------------------------------------------------------------
# Format 6: DOCX (.docx)
# -------------------------------------------------------------------
def test_parse_valid_docx():
    docx_bytes = make_minimal_docx("Client requirement: Support OAuth 2.0 with Google and GitHub.")
    res = document_dispatcher.parse_document(docx_bytes, "requirements.docx")
    assert res.file_type == "docx"
    assert "Support OAuth 2.0 with Google and GitHub" in res.extracted_text
    assert res.metadata["paragraph_count"] >= 1


# -------------------------------------------------------------------
# Error Cases: Empty Files (0 Bytes)
# -------------------------------------------------------------------
@pytest.mark.parametrize("filename", [
    "empty.txt",
    "empty.md",
    "empty.csv",
    "empty.json",
    "empty.pdf",
    "empty.docx",
])
def test_empty_files_rejected(filename):
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(b"", filename)
    assert "empty" in str(exc_info.value).lower()


# -------------------------------------------------------------------
# Error Cases: Corrupted Files
# -------------------------------------------------------------------
def test_corrupted_pdf_rejected():
    # Corrupt PDF header
    corrupt_bytes = b"NOT_A_PDF_STREAM_RANDOM_DATA_1234567890"
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(corrupt_bytes, "broken.pdf")
    assert "missing %pdf" in str(exc_info.value).lower()


def test_corrupted_docx_rejected():
    # Missing zip header or corrupted zip
    corrupt_bytes = b"PK\x03\x04CORRUPTED_ZIP_BODY_DATA"
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(corrupt_bytes, "broken.docx")
    assert "corrupt" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


def test_corrupted_json_rejected():
    corrupt_json = b'{"decision": "Incomplete string without closing brace'
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(corrupt_json, "broken.json")
    assert "invalid json" in str(exc_info.value).lower() or "corrupt" in str(exc_info.value).lower()


# -------------------------------------------------------------------
# Error Cases: Unsupported and Invalid Extensions
# -------------------------------------------------------------------
def test_unsupported_file_extension():
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(b"echo Hello", "script.sh")
    assert "unsupported document format '.sh'" in str(exc_info.value).lower()


def test_missing_file_extension():
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(b"Some text", "no_extension_file")
    assert "missing a valid file extension" in str(exc_info.value).lower()
