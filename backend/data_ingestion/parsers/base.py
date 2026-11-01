from abc import ABC, abstractmethod
from typing import Dict, Any
from ..schemas import DocumentParseResult


class DocumentParsingError(Exception):
    """Raised when document parsing fails due to corruption, formatting, or parsing error."""
    pass


class BaseDocumentParser(ABC):
    """Abstract base class for all multi-source document parsers."""

    @abstractmethod
    def parse(self, content: bytes, filename: str) -> DocumentParseResult:
        """
        Extract structured text and metadata from raw document bytes.

        :param content: Binary file content
        :param filename: Original file name including extension
        :return: DocumentParseResult
        :raises DocumentParsingError: if content is corrupt, empty, or unparseable
        """
        pass

