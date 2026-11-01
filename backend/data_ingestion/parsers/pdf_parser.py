import io
import re
import zlib
from typing import Dict, Any, List

from .base import BaseDocumentParser, DocumentParsingError
from ..schemas import DocumentParseResult
from ..normalizer import text_normalizer, TextNormalizationError


class PDFDocumentParser(BaseDocumentParser):
    """
    Parses PDF documents.
    Uses pypdf if installed; includes built-in pure-Python fallback for FlateDecode
    and text stream decompression.
    """

    def parse(self, content: bytes, filename: str) -> DocumentParseResult:
        if not content or len(content) == 0:
            raise DocumentParsingError(f"PDF document {filename} is empty (0 bytes).")

        # Validate PDF magic header
        if b"%PDF-" not in content[:1024]:
            raise DocumentParsingError(f"Invalid or corrupted PDF file {filename}: missing %PDF magic header.")

        extracted_text = ""
        page_count = 0
        metadata: Dict[str, Any] = {"format": "pdf"}

        # Attempt 1: Try pypdf if available
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                raise DocumentParsingError(f"PDF file {filename} is encrypted/password-protected.")

            page_count = len(reader.pages)
            pages_text = []
            for i, page in enumerate(reader.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    pages_text.append(txt.strip())

            extracted_text = "\n\n".join(pages_text)
            if reader.metadata:
                metadata["title"] = reader.metadata.title or None
                metadata["author"] = reader.metadata.author or None
        except DocumentParsingError:
            raise
        except Exception:
            # Attempt 2: Built-in pure-Python text and stream extractor
            extracted_text, page_count = self._pure_python_pdf_extract(content, filename)

        if not extracted_text or not extracted_text.strip():
            # If after both attempts no text was found (e.g. image-only or empty)
            raise DocumentParsingError(
                f"No extractable text found in PDF {filename}. The document may be empty, image-only, or corrupted."
            )

        try:
            cleaned_text, stats = text_normalizer.normalize(extracted_text, filename)
        except TextNormalizationError as e:
            raise DocumentParsingError(str(e)) from e

        metadata["page_count"] = page_count or 1
        metadata.update(stats)

        return DocumentParseResult(
            filename=filename,
            file_type="pdf",
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            extracted_text=cleaned_text,
            metadata=metadata
        )

    def _pure_python_pdf_extract(self, content: bytes, filename: str) -> tuple[str, int]:
        """Built-in stream extractor that decompresses flate streams and extracts PDF text objects."""
        text_parts: List[str] = []

        # Count pages approximately
        page_count = max(len(re.findall(rb"/Type\s*/Page\b", content)), 1)

        # Find all stream ... endstream blocks
        stream_matches = re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", content, re.DOTALL)
        for match in stream_matches:
            stream_data = match.group(1)
            # Try to decompress FlateDecode stream
            try:
                decompressed = zlib.decompress(stream_data)
            except Exception:
                # Might be uncompressed stream or different filter
                decompressed = stream_data

            # Extract text within parentheses: (Sample text) Tj or (Sample) '
            tj_matches = re.findall(rb"\((.*?)\)\s*(?:Tj|'|\")", decompressed)
            for m in tj_matches:
                try:
                    text_parts.append(m.decode("utf-8", errors="replace"))
                except Exception:
                    pass

            # Extract text arrays: [(Part1) 10 (Part2)] TJ
            array_matches = re.findall(rb"\[(.*?)\]\s*TJ", decompressed)
            for arr in array_matches:
                inner_strings = re.findall(rb"\((.*?)\)", arr)
                for s in inner_strings:
                    try:
                        text_parts.append(s.decode("utf-8", errors="replace"))
                    except Exception:
                        pass

        extracted = " ".join(text_parts).strip()
        # Clean up PDF string escapes
        extracted = extracted.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
        return extracted, page_count
