import csv
import io
import json
import os
from typing import Any, Dict

from .base import BaseDocumentParser, DocumentParsingError
from ..schemas import DocumentParseResult
from ..normalizer import text_normalizer, TextNormalizationError


class TextDocumentParser(BaseDocumentParser):
    """Parses plain text (.txt), Markdown (.md), CSV (.csv), and JSON (.json) documents."""

    def parse(self, content: bytes, filename: str) -> DocumentParseResult:
        if not content or len(content) == 0:
            raise DocumentParsingError(f"Document {filename} is empty (0 bytes).")

        ext = os.path.splitext(filename)[1].lower()

        # Try UTF-8 first, fallback to latin-1
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = content.decode("latin-1")
            except Exception as e:
                raise DocumentParsingError(f"Failed to decode text file {filename}: {e}")

        if ext == ".csv":
            extracted_text, metadata = self._parse_csv(raw_text, filename)
        elif ext == ".json":
            extracted_text, metadata = self._parse_json(raw_text, filename)
        else:
            extracted_text = raw_text
            metadata = {"format": "markdown" if ext == ".md" else "plain_text"}

        try:
            cleaned_text, stats = text_normalizer.normalize(extracted_text, filename)
        except TextNormalizationError as e:
            raise DocumentParsingError(str(e)) from e

        metadata.update(stats)
        file_type = ext.lstrip(".") or "text"

        return DocumentParseResult(
            filename=filename,
            file_type=file_type,
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            extracted_text=cleaned_text,
            metadata=metadata
        )

    def _parse_csv(self, raw_text: str, filename: str) -> tuple[str, Dict[str, Any]]:
        """Parses CSV and generates formatted textual representation."""
        try:
            reader = csv.reader(io.StringIO(raw_text))
            rows = list(reader)
        except Exception as e:
            raise DocumentParsingError(f"Malformed CSV content in {filename}: {e}")

        if not rows:
            raise DocumentParsingError(f"CSV file {filename} contains no rows.")

        header = rows[0]
        data_rows = rows[1:]

        formatted_lines = [f"CSV Document: {filename} (Columns: {', '.join(header)})"]
        for idx, row in enumerate(data_rows, start=1):
            row_items = []
            for col_idx, val in enumerate(row):
                col_name = header[col_idx] if col_idx < len(header) else f"Col_{col_idx+1}"
                row_items.append(f"{col_name}: {val.strip()}")
            formatted_lines.append(f"Row {idx}: " + "; ".join(row_items))

        text_output = "\n".join(formatted_lines)
        metadata = {
            "format": "csv",
            "column_count": len(header),
            "row_count": len(data_rows),
            "columns": header,
        }
        return text_output, metadata

    def _parse_json(self, raw_text: str, filename: str) -> tuple[str, Dict[str, Any]]:
        """Parses JSON and generates readable key-value and transcript text."""
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise DocumentParsingError(f"Corrupt or invalid JSON in {filename}: {e}")

        def format_json_node(obj: Any, indent: int = 0) -> str:
            prefix = "  " * indent
            if isinstance(obj, dict):
                lines = []
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        lines.append(format_json_node(v, indent + 1))
                    else:
                        lines.append(f"{prefix}{k}: {v}")
                return "\n".join(lines)
            elif isinstance(obj, list):
                lines = []
                for idx, item in enumerate(obj, start=1):
                    if isinstance(item, (dict, list)):
                        lines.append(f"{prefix}- Item {idx}:")
                        lines.append(format_json_node(item, indent + 1))
                    else:
                        lines.append(f"{prefix}- {item}")
                return "\n".join(lines)
            else:
                return f"{prefix}{obj}"

        text_output = format_json_node(data)
        metadata = {
            "format": "json",
            "root_type": type(data).__name__,
        }
        return text_output, metadata
