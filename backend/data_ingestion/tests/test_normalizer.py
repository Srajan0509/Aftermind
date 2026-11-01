import pytest
from data_ingestion.normalizer import TextNormalizer, TextNormalizationError, text_normalizer


def test_normalizer_cleans_whitespace_and_control_chars():
    dirty_text = "  Meeting Notes \r\n\r\n Line 1\x00\x08 with text.\u00a0\n\n\n\nLine 2   "
    cleaned, stats = text_normalizer.normalize(dirty_text, "notes.txt")

    assert "\x00" not in cleaned
    assert "\x08" not in cleaned
    assert "\r" not in cleaned
    assert "\u00a0" not in cleaned
    assert "\n\n\n" not in cleaned  # collapsed excessive newlines
    assert "Meeting Notes\n\nLine 1 with text.\n\nLine 2" == cleaned
    assert stats["word_count"] > 0
    assert stats["character_count"] == len(cleaned)


def test_normalizer_rejects_empty_and_whitespace():
    with pytest.raises(TextNormalizationError):
        text_normalizer.normalize("", "empty.txt")

    with pytest.raises(TextNormalizationError):
        text_normalizer.normalize("   \n\t   ", "spaces.txt")


def test_normalizer_rejects_oversized_text():
    tiny_normalizer = TextNormalizer(max_characters=50)
    long_text = "A" * 51
    with pytest.raises(TextNormalizationError) as exc_info:
        tiny_normalizer.normalize(long_text, "huge.txt")
    assert "exceeds the maximum limit" in str(exc_info.value)


def test_normalizer_handles_bytes_input():
    byte_content = b"Decision: Approved project budget of $10,000.\nTarget start date is Monday."
    cleaned, stats = text_normalizer.normalize(byte_content, "raw.txt")
    assert "Approved project budget" in cleaned
    assert stats["character_count"] == len(cleaned)

