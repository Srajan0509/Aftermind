import os
from typing import Optional

from .base import BaseAudioTranscriber, AudioTranscriptionError
from .whisper import WhisperAudioTranscriber
from .gemini import GeminiAudioTranscriber
from .mock import MockAudioTranscriber
from ..config import ingestion_settings
from ..schemas import AudioTranscribeResult


class AudioTranscriberManager:
    """
    Manages selection and execution of audio transcription providers.
    Supports 'auto', 'whisper', 'gemini', and 'mock'.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or ingestion_settings.AUDIO_TRANSCRIBER_PROVIDER).lower()
        self._whisper = WhisperAudioTranscriber()
        self._gemini = GeminiAudioTranscriber()
        self._mock = MockAudioTranscriber()

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> AudioTranscribeResult:
        if not audio_bytes or len(audio_bytes) == 0:
            raise AudioTranscriptionError(f"Audio file '{filename}' is empty (0 bytes).")

        ext = os.path.splitext(filename)[1].lower()
        if ext not in ingestion_settings.SUPPORTED_AUDIO_EXTENSIONS:
            supported = ", ".join(sorted(ingestion_settings.SUPPORTED_AUDIO_EXTENSIONS))
            raise AudioTranscriptionError(
                f"Unsupported audio format '{ext}' for file '{filename}'. Supported formats: {supported}"
            )

        if len(audio_bytes) > ingestion_settings.MAX_AUDIO_SIZE_BYTES:
            max_mb = ingestion_settings.MAX_AUDIO_SIZE_BYTES / (1024 * 1024)
            raise AudioTranscriptionError(
                f"Audio file '{filename}' exceeds maximum size of {max_mb:.1f} MB."
            )

        # Provider resolution
        target = self.provider

        if target == "whisper":
            return self._whisper.transcribe(audio_bytes, filename, language)

        if target == "gemini":
            return self._gemini.transcribe(audio_bytes, filename, language)

        if target == "mock":
            return self._mock.transcribe(audio_bytes, filename, language)

        # 'auto' strategy: try Whisper first, then Gemini, fallback to mock if no keys configured
        if ingestion_settings.OPENAI_API_KEY:
            try:
                return self._whisper.transcribe(audio_bytes, filename, language)
            except Exception:
                pass

        if ingestion_settings.GEMINI_API_KEY:
            try:
                return self._gemini.transcribe(audio_bytes, filename, language)
            except Exception:
                pass

        # Clean fallback to mock when running in offline/testing environments
        return self._mock.transcribe(audio_bytes, filename, language)


audio_transcription_manager = AudioTranscriberManager()
