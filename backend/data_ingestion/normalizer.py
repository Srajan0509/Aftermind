import re
import unicodedata
from typing import Dict, Any, Tuple


class TextNormalizationError(ValueError):
    """Raised when text normalization fails or violates size constraints."""
    pass


class TextNormalizer:
    """
    Cleans, normalizes, and validates text extracted from multi-source inputs
    before persistence in Module 3 and extraction in Module 2.
    """

    def __init__(self, max_characters: int = 100000):
        self.max_characters = max_characters

    def normalize(self, raw_text: str, filename: str = "input") -> Tuple[str, Dict[str, Any]]:
        """
        Cleans and standardizes raw text:
        1. Validates non-empty
        2. Unicode normalization (NFC)
        3. Strips unprintable control characters
        4. Normalizes newlines and whitespace
        5. Enforces maximum character constraints
        6. Extracts metadata stats
        """
        if raw_text is None:
            raise TextNormalizationError(f"Raw text for {filename} cannot be None.")

        # Decode if bytes passed
        if isinstance(raw_text, bytes):
            try:
                raw_text = raw_text.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    raw_text = raw_text.decode("latin-1")
                except Exception as e:
                    raise TextNormalizationError(f"Failed to decode text bytes for {filename}: {e}")

        # Unicode normalization
        text = unicodedata.normalize("NFC", raw_text)

        # Replace carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace non-breaking and unusual spaces
        text = text.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")

        # Strip unprintable control characters, preserving \n and \t
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        # Strip leading and trailing spaces on each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Collapse more than 3 consecutive newlines down to 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip outer whitespace
        cleaned = text.strip()

        if not cleaned:
            raise TextNormalizationError(f"Extracted text from {filename} is empty or contains only whitespace.")

        if len(cleaned) > self.max_characters:
            raise TextNormalizationError(
                f"Extracted text from {filename} has {len(cleaned)} characters, "
                f"which exceeds the maximum limit of {self.max_characters} characters."
            )

        words = len(re.findall(r"\b\w+\b", cleaned))
        char_count = len(cleaned)
        line_count = len(cleaned.splitlines())

        stats = {
            "character_count": char_count,
            "word_count": words,
            "line_count": line_count,
        }

        return cleaned, stats


text_normalizer = TextNormalizer()
