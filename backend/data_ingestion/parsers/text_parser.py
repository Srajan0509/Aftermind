import os
from typing import Dict, Any

from .base import BaseDocumentParser, DocumentParsingError
from ..schemas import DocumentParseResult
from ..normalizer import text_normalizer, TextNormalizationError


class TextDocumentParser(BaseDocumentParser):
    """
    Parses plain text (.txt) documents.
    Detects encoding, verifies non-binary content, and standardizes whitespace.
    """

    def parse(self, content: bytes, filename: str) -> DocumentParseResult:
        if not content or len(content) == 0:
            raise DocumentParsingError(f"Text document '{filename}' is empty (0 bytes).")

        # Security check: detect binary executable signatures or high density of null bytes
        if content.startswith(b"MZ") or content.startswith(b"\x7fELF") or content.startswith(b"\xca\xfe\xba\xbe"):
            raise DocumentParsingError(
                f"MIME/format mismatch in '{filename}': File extension is .txt but content is a binary executable."
            )

        # Check for null bytes indicating binary data
        sample = content[:1024]
        if b"\x00" in sample:
            raise DocumentParsingError(
                f"MIME/format mismatch in '{filename}': File extension is .txt but contains binary/null bytes."
            )

        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = content.decode("latin-1")
            except Exception as e:
                raise DocumentParsingError(f"Failed to decode text file '{filename}': {e}") from e

        try:
            cleaned_text, stats = text_normalizer.normalize(raw_text, filename)
        except TextNormalizationError as e:
            raise DocumentParsingError(str(e)) from e

        metadata: Dict[str, Any] = {
            "format": "plain_text",
            "file_size_bytes": len(content),
        }
        metadata.update(stats)

        return DocumentParseResult(
            filename=filename,
            file_type="txt",
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            extracted_text=cleaned_text,
            metadata=metadata
        )
