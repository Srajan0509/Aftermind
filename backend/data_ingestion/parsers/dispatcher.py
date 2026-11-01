import os
from typing import Dict, Type

from .base import BaseDocumentParser, DocumentParsingError
from .text_parser import TextDocumentParser
from .pdf_parser import PDFDocumentParser
from .docx_parser import DOCXDocumentParser
from ..config import ingestion_settings
from ..schemas import DocumentParseResult


class DocumentParserDispatcher:
    """
    Dispatcher that routes files by extension to their specialized document parser.
    Supports .txt, .md, .pdf, .docx, .csv, .json.
    """

    def __init__(self):
        self._text_parser = TextDocumentParser()
        self._pdf_parser = PDFDocumentParser()
        self._docx_parser = DOCXDocumentParser()

        self._parsers: Dict[str, BaseDocumentParser] = {
            ".txt": self._text_parser,
            ".md": self._text_parser,
            ".csv": self._text_parser,
            ".json": self._text_parser,
            ".pdf": self._pdf_parser,
            ".docx": self._docx_parser,
        }

    def parse_document(self, content: bytes, filename: str) -> DocumentParseResult:
        """
        Parses document based on file extension.

        :param content: Binary file content
        :param filename: Original file name
        :return: DocumentParseResult
        :raises DocumentParsingError: for unsupported extensions, oversize files, or parsing errors
        """
        if not filename or "." not in filename:
            raise DocumentParsingError(f"Filename '{filename}' is missing a valid file extension.")

        ext = os.path.splitext(filename)[1].lower()

        if ext not in ingestion_settings.SUPPORTED_DOCUMENT_EXTENSIONS:
            supported = ", ".join(sorted(ingestion_settings.SUPPORTED_DOCUMENT_EXTENSIONS))
            raise DocumentParsingError(
                f"Unsupported document format '{ext}' for file '{filename}'. Supported formats: {supported}"
            )

        if len(content) > ingestion_settings.MAX_DOCUMENT_SIZE_BYTES:
            max_mb = ingestion_settings.MAX_DOCUMENT_SIZE_BYTES / (1024 * 1024)
            raise DocumentParsingError(
                f"File '{filename}' exceeds maximum document size of {max_mb:.1f} MB."
            )

        parser = self._parsers[ext]
        return parser.parse(content=content, filename=filename)


document_dispatcher = DocumentParserDispatcher()
