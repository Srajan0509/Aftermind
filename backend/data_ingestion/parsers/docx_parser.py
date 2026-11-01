import io
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from .base import BaseDocumentParser, DocumentParsingError
from ..schemas import DocumentParseResult
from ..normalizer import text_normalizer, TextNormalizationError

# XML namespaces standard in Microsoft Office Open XML (.docx)
WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CORE_PROP_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"


class DOCXDocumentParser(BaseDocumentParser):
    """
    Parses Microsoft Word (.docx) documents.
    Uses built-in zipfile and ElementTree to parse word/document.xml with zero external dependencies.
    """

    def parse(self, content: bytes, filename: str) -> DocumentParseResult:
        if not content or len(content) == 0:
            raise DocumentParsingError(f"Word document {filename} is empty (0 bytes).")

        # Validate ZIP magic signature (PK\x03\x04)
        if not content.startswith(b"PK\x03\x04"):
            raise DocumentParsingError(
                f"Invalid or corrupted DOCX file {filename}: missing ZIP magic header."
            )

        metadata: Dict[str, Any] = {"format": "docx"}
        paragraphs: List[str] = []

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Validate presence of word/document.xml
                if "word/document.xml" not in zf.namelist():
                    raise DocumentParsingError(
                        f"Invalid DOCX file {filename}: missing word/document.xml."
                    )

                # Parse document text
                xml_content = zf.read("word/document.xml")
                root = ET.fromstring(xml_content)

                for p_elem in root.iter(f"{{{WORD_NAMESPACE}}}p"):
                    p_text_parts = []
                    for t_elem in p_elem.iter(f"{{{WORD_NAMESPACE}}}t"):
                        if t_elem.text:
                            p_text_parts.append(t_elem.text)
                    if p_text_parts:
                        paragraphs.append("".join(p_text_parts))

                # Extract core properties if available (author, title)
                if "docProps/core.xml" in zf.namelist():
                    try:
                        core_xml = zf.read("docProps/core.xml")
                        core_root = ET.fromstring(core_xml)
                        title_elem = core_root.find(f"{{{DC_NAMESPACE}}}title")
                        if title_elem is not None and title_elem.text:
                            metadata["title"] = title_elem.text
                        creator_elem = core_root.find(f"{{{DC_NAMESPACE}}}creator")
                        if creator_elem is not None and creator_elem.text:
                            metadata["author"] = creator_elem.text
                    except Exception:
                        pass
        except zipfile.BadZipFile as e:
            raise DocumentParsingError(f"Corrupted or invalid DOCX archive {filename}: {e}")
        except ET.ParseError as e:
            raise DocumentParsingError(f"Corrupted XML structure in DOCX file {filename}: {e}")

        extracted_text = "\n\n".join(paragraphs).strip()

        if not extracted_text:
            raise DocumentParsingError(
                f"No extractable text found in DOCX file {filename}. The document is blank."
            )

        try:
            cleaned_text, stats = text_normalizer.normalize(extracted_text, filename)
        except TextNormalizationError as e:
            raise DocumentParsingError(str(e)) from e

        metadata["paragraph_count"] = len(paragraphs)
        metadata.update(stats)

        return DocumentParseResult(
            filename=filename,
            file_type="docx",
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            extracted_text=cleaned_text,
            metadata=metadata
        )
