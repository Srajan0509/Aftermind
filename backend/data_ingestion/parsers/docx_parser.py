import io
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

from .base import BaseDocumentParser, DocumentParsingError
from ..schemas import DocumentParseResult
from ..normalizer import text_normalizer, TextNormalizationError

# Standard XML namespaces for Microsoft Word Open XML
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CORE_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"


class DOCXDocumentParser(BaseDocumentParser):
    """
    Parses Microsoft Word (.docx) documents.
    Extracts paragraphs, text runs, and document metadata (title, author, revision, timestamps)
    using standard Open XML structures with secure ZIP handling.
    """

    def parse(self, content: bytes, filename: str) -> DocumentParseResult:
        if not content or len(content) == 0:
            raise DocumentParsingError(f"Word document '{filename}' is empty (0 bytes).")

        # MIME / magic byte check for ZIP header
        if not content.startswith(b"PK\x03\x04"):
            raise DocumentParsingError(
                f"MIME/format mismatch in '{filename}': File extension is .docx but content lacks PK ZIP magic header."
            )

        metadata: Dict[str, Any] = {"format": "docx"}
        paragraphs: List[str] = []

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Validate presence of word/document.xml
                namelist = zf.namelist()
                if "word/document.xml" not in namelist:
                    raise DocumentParsingError(
                        f"Invalid DOCX document '{filename}': Archive does not contain word/document.xml."
                    )

                # Parse paragraphs and text runs
                xml_data = zf.read("word/document.xml")
                root = ET.fromstring(xml_data)

                for p_elem in root.iter(f"{{{WORD_NS}}}p"):
                    p_parts = []
                    for t_elem in p_elem.iter(f"{{{WORD_NS}}}t"):
                        if t_elem.text:
                            p_parts.append(t_elem.text)
                    if p_parts:
                        paragraphs.append("".join(p_parts))

                # Extract metadata from docProps/core.xml if present
                if "docProps/core.xml" in namelist:
                    try:
                        core_data = zf.read("docProps/core.xml")
                        core_root = ET.fromstring(core_data)

                        title = core_root.find(f"{{{DC_NS}}}title")
                        if title is not None and title.text:
                            metadata["title"] = title.text.strip()

                        creator = core_root.find(f"{{{DC_NS}}}creator")
                        if creator is not None and creator.text:
                            metadata["author"] = creator.text.strip()

                        subject = core_root.find(f"{{{DC_NS}}}subject")
                        if subject is not None and subject.text:
                            metadata["subject"] = subject.text.strip()

                        revision = core_root.find(f"{{{CP_NS}}}revision")
                        if revision is not None and revision.text:
                            metadata["revision"] = revision.text.strip()

                        created = core_root.find(f"{{{DCTERMS_NS}}}created")
                        if created is not None and created.text:
                            metadata["created_date"] = created.text.strip()

                        modified = core_root.find(f"{{{DCTERMS_NS}}}modified")
                        if modified is not None and modified.text:
                            metadata["modified_date"] = modified.text.strip()
                    except Exception:
                        pass
        except zipfile.BadZipFile as e:
            raise DocumentParsingError(f"Corrupted or invalid DOCX archive in '{filename}': {e}") from e
        except ET.ParseError as e:
            raise DocumentParsingError(f"Corrupted XML structure in DOCX '{filename}': {e}") from e

        extracted_text = "\n\n".join(paragraphs).strip()

        if not extracted_text:
            raise DocumentParsingError(
                f"No extractable text found in DOCX file '{filename}'. The document is blank."
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
