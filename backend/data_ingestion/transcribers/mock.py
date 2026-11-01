import os
from typing import Optional

from .base import BaseAudioTranscriber, AudioTranscriptionError
from ..schemas import AudioTranscribeResult
from ..normalizer import text_normalizer


class MockAudioTranscriber(BaseAudioTranscriber):
    """
    Deterministic audio transcriber for test environments, offline execution,
    and fallback operation without external API calls.
    """

    def __init__(self, fixed_text: Optional[str] = None):
        self.fixed_text = fixed_text

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> AudioTranscribeResult:
        if not audio_bytes or len(audio_bytes) == 0:
            raise AudioTranscriptionError(f"Audio file {filename} is empty (0 bytes).")

        ext = os.path.splitext(filename)[1].lower().lstrip(".")

        if self.fixed_text:
            text = self.fixed_text
        else:
            text = (
                f"Audio recording transcript from {filename}: The team met to discuss project deliverables. "
                f"We agreed on completing the milestone by next Friday. John committed to preparing the report."
            )

        cleaned_text, stats = text_normalizer.normalize(text, filename)

        return AudioTranscribeResult(
            filename=filename,
            audio_format=ext or "audio",
            duration_seconds=30.0,
            language=language or "en",
            transcript=cleaned_text,
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            provider_used="mock_transcriber",
            metadata={"simulated": True, "file_size_bytes": len(audio_bytes)}
        )
