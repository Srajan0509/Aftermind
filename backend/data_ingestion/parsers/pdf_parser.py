import os
from typing import Dict, Any, List

from .base import BaseDocumentParser, DocumentParsingError
from ..schemas import DocumentParseResult
from ..normalizer import text_normalizer, TextNormalizationError


class PDFDocumentParser(BaseDocumentParser):
    """
    Parses PDF documents using PyMuPDF (fitz).
    Reliably extracts text streams, metadata, and page counts while guarding
    against encrypted, malformed, or MIME-mismatched files.
    """

    def parse(self, content: bytes, filename: str) -> DocumentParseResult:
        if not content or len(content) == 0:
            raise DocumentParsingError(f"PDF document '{filename}' is empty (0 bytes).")

        # MIME / magic bytes verification
        if b"%PDF-" not in content[:1024]:
            raise DocumentParsingError(
                f"MIME/format mismatch in '{filename}': File extension is .pdf but content lacks %PDF magic header."
            )

        try:
            import fitz
        except ImportError as e:
            raise DocumentParsingError(
                "PyMuPDF ('fitz') is required for PDF parsing. Please install pymupdf."
            ) from e

        doc = None
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            if doc.is_encrypted:
                raise DocumentParsingError(
                    f"PDF document '{filename}' is encrypted or password-protected."
                )

            page_count = doc.page_count
            pages_text: List[str] = []

            for page_num in range(page_count):
                page = doc.load_page(page_num)
                page_text = page.get_text("text") or ""
                if page_text.strip():
                    pages_text.append(page_text.strip())

            extracted_text = "\n\n".join(pages_text).strip()

            metadata: Dict[str, Any] = {
                "format": "pdf",
                "page_count": page_count,
            }

            # Extract document metadata
            doc_meta = doc.metadata or {}
            if doc_meta.get("title"):
                metadata["title"] = doc_meta["title"].strip()
            if doc_meta.get("author"):
                metadata["author"] = doc_meta["author"].strip()
            if doc_meta.get("creationDate"):
                metadata["creation_date"] = doc_meta["creationDate"].strip()
            if doc_meta.get("modDate"):
                metadata["modified_date"] = doc_meta["modDate"].strip()
            if doc_meta.get("subject"):
                metadata["subject"] = doc_meta["subject"].strip()

        except DocumentParsingError:
            raise
        except Exception as e:
            raise DocumentParsingError(f"Failed to parse PDF document '{filename}': {e}") from e
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass

        if not extracted_text:
            raise DocumentParsingError(
                f"No extractable text found in PDF '{filename}'. The document is blank or contains only images."
            )

        try:
            cleaned_text, stats = text_normalizer.normalize(extracted_text, filename)
        except TextNormalizationError as e:
            raise DocumentParsingError(str(e)) from e

        metadata.update(stats)

        return DocumentParseResult(
            filename=filename,
            file_type="pdf",
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            extracted_text=cleaned_text,
            metadata=metadata
        )
