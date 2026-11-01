import io
import zipfile
import pytest
import fitz

from data_ingestion.parsers.dispatcher import document_dispatcher
from data_ingestion.parsers.base import DocumentParsingError


def make_pdf_with_fitz(text: str, title: str = "Test Spec", author: str = "Engineering Team") -> bytes:
    """Creates a valid PDF using PyMuPDF (fitz) with metadata and text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.set_metadata({
        "title": title,
        "author": author,
        "subject": "Business Memory Ingestion",
    })
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def make_docx_with_metadata(
    text: str,
    title: str = "Business Requirements",
    author: str = "Product Manager",
    revision: str = "2"
) -> bytes:
    """Creates a valid DOCX file with word/document.xml and docProps/core.xml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '</Types>'
        )
        doc_xml = (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            f'<w:p><w:r><w:t>{text}</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Second paragraph discussing milestones and payment gateway.</w:t></w:r></w:p>'
            '</w:body>'
            '</w:document>'
        )
        zf.writestr("word/document.xml", doc_xml)

        core_xml = (
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/">'
            f'<dc:title>{title}</dc:title>'
            f'<dc:creator>{author}</dc:creator>'
            f'<cp:revision>{revision}</cp:revision>'
            '<dcterms:created>2026-10-31T10:00:00Z</dcterms:created>'
            '</cp:coreProperties>'
        )
        zf.writestr("docProps/core.xml", core_xml)

    return buf.getvalue()


# -------------------------------------------------------------------
# Format 1: PDF (.pdf) via PyMuPDF (fitz)
# -------------------------------------------------------------------
def test_parse_valid_pdf_with_pymupdf():
    content = make_pdf_with_fitz(
        text="The client ABC Technologies approved Stripe payment integration. Deadline December 20, 2026.",
        title="Payment Architecture Document",
        author="Srajan"
    )
    res = document_dispatcher.parse_document(content, "payment_arch.pdf")

    assert res.file_type == "pdf"
    assert "approved Stripe payment integration" in res.extracted_text
    assert res.metadata["title"] == "Payment Architecture Document"
    assert res.metadata["author"] == "Srajan"
    assert res.metadata["page_count"] == 1
    assert res.word_count > 0


# -------------------------------------------------------------------
# Format 2: Word Document (.docx)
# -------------------------------------------------------------------
def test_parse_valid_docx_with_metadata():
    content = make_docx_with_metadata(
        text="Client commitment: John will deliver the SSO authentication module by Monday.",
        title="SSO Specification",
        author="Alice",
        revision="3"
    )
    res = document_dispatcher.parse_document(content, "sso_spec.docx")

    assert res.file_type == "docx"
    assert "SSO authentication module by Monday" in res.extracted_text
    assert "Second paragraph discussing milestones" in res.extracted_text
    assert res.metadata["title"] == "SSO Specification"
    assert res.metadata["author"] == "Alice"
    assert res.metadata["revision"] == "3"
    assert res.metadata["paragraph_count"] == 2


# -------------------------------------------------------------------
# Format 3: Plain Text (.txt)
# -------------------------------------------------------------------
def test_parse_valid_txt():
    content = b"Decision: We agreed on a 2-week sprint cycle.\nNext review is on November 15, 2026."
    res = document_dispatcher.parse_document(content, "sprint_review.txt")

    assert res.file_type == "txt"
    assert "agreed on a 2-week sprint cycle" in res.extracted_text
    assert res.metadata["format"] == "plain_text"
    assert res.word_count > 0


# -------------------------------------------------------------------
# Error Cases: Empty Files (0 Bytes)
# -------------------------------------------------------------------
@pytest.mark.parametrize("filename", [
    "empty.pdf",
    "empty.docx",
    "empty.txt",
])
def test_empty_files_rejected(filename):
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(b"", filename)
    assert "empty" in str(exc_info.value).lower()


# -------------------------------------------------------------------
# Error Cases: Corrupted Files
# -------------------------------------------------------------------
def test_corrupted_pdf_rejected():
    corrupt_pdf = b"%PDF-1.4\nCorrupted binary junk content that fails MuPDF parsing\x00\xff\xee"
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(corrupt_pdf, "broken.pdf")
    assert "failed to parse pdf" in str(exc_info.value).lower() or "no extractable text" in str(exc_info.value).lower()


def test_corrupted_docx_rejected():
    corrupt_docx = b"PK\x03\x04INVALID_TRUNCATED_ZIP_ARCHIVE"
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(corrupt_docx, "broken.docx")
    assert "corrupt" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()


# -------------------------------------------------------------------
# Error Cases: MIME / Magic Bytes Mismatches
# -------------------------------------------------------------------
def test_mime_mismatch_pdf_containing_plain_text():
    # Plain text saved with .pdf extension
    fake_pdf = b"This is just plain text, not a valid PDF binary file."
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(fake_pdf, "spoofed.pdf")
    assert "mime/format mismatch" in str(exc_info.value).lower()


def test_mime_mismatch_docx_containing_plain_text():
    # Plain text saved with .docx extension
    fake_docx = b"This is plain text without a PK zip magic header."
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(fake_docx, "spoofed.docx")
    assert "mime/format mismatch" in str(exc_info.value).lower()


def test_mime_mismatch_txt_containing_binary_executable():
    # Executable DOS/Windows MZ header saved with .txt extension
    fake_txt = b"MZ\x90\x00\x03\x00\x00\x00This is a binary executable"
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(fake_txt, "malware.txt")
    assert "mime/format mismatch" in str(exc_info.value).lower()


# -------------------------------------------------------------------
# Error Cases: Unsupported and Invalid Extensions
# -------------------------------------------------------------------
def test_unsupported_document_extension():
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(b"echo 'run script'", "deploy.sh")
    assert "unsupported document format '.sh'" in str(exc_info.value).lower()


def test_missing_document_extension():
    with pytest.raises(DocumentParsingError) as exc_info:
        document_dispatcher.parse_document(b"Notes without extension", "meeting_notes")
    assert "missing a valid file extension" in str(exc_info.value).lower()
