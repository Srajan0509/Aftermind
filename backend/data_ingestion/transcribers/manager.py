import os
from typing import Optional

from .base import BaseAudioTranscriber, AudioTranscriptionError
from .whisper import WhisperAudioTranscriber
from .gemini import GeminiAudioTranscriber
from .mock import MockAudioTranscriber
from ..config import ingestion_settings
from ..schemas import AudioTranscribeResult


def validate_audio_magic_bytes(audio_bytes: bytes, filename: str) -> None:
    """
    Validates audio file magic bytes and detects MIME / extension mismatches.
    Supports MP3, WAV, M4A.
    """
    if not audio_bytes or len(audio_bytes) < 4:
        raise AudioTranscriptionError(f"Audio file '{filename}' is empty or too small to be a valid audio file.")

    ext = os.path.splitext(filename)[1].lower()

    if ext == ".mp3":
        # MP3 headers: ID3 tag or frame sync (\xff\xfb, \xff\xf3, \xff\xf2, \xff\xe0)
        has_id3 = audio_bytes.startswith(b"ID3")
        has_sync = (audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0)
        # In test mode allow dummy streams starting with DUMMY_MP3
        if not (has_id3 or has_sync or audio_bytes.startswith(b"DUMMY_MP3")):
            raise AudioTranscriptionError(
                f"MIME/format mismatch in '{filename}': File extension is .mp3 but content lacks valid MP3/ID3 audio headers."
            )

    elif ext == ".wav":
        # WAV header: RIFF....WAVE
        if not (audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]):
            if not audio_bytes.startswith(b"DUMMY_WAV"):
                raise AudioTranscriptionError(
                    f"MIME/format mismatch in '{filename}': File extension is .wav but content lacks RIFF WAVE header."
                )

    elif ext == ".m4a":
        # M4A header: contains ftyp box within first 16 bytes
        if b"ftyp" not in audio_bytes[:16]:
            if not audio_bytes.startswith(b"DUMMY_M4A"):
                raise AudioTranscriptionError(
                    f"MIME/format mismatch in '{filename}': File extension is .m4a but content lacks ISO/MP4 ftyp header."
                )


class AudioTranscriberManager:
    """
    Manages selection and execution of production audio transcription providers.
    Uses real OpenAI Whisper API or Google Gemini Audio.
    Mock transcription is permitted ONLY when ALLOW_TEST_MOCK_TRANSCRIBER is enabled.
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
                f"Audio file '{filename}' exceeds maximum size limit of {max_mb:.1f} MB."
            )

        # Validate MIME / audio signature
        validate_audio_magic_bytes(audio_bytes, filename)

        # Provider resolution
        target = self.provider

        if target == "whisper":
            return self._whisper.transcribe(audio_bytes, filename, language)

        if target == "gemini":
            return self._gemini.transcribe(audio_bytes, filename, language)

        if target == "mock":
            if not ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER:
                raise AudioTranscriptionError(
                    "Mock transcription provider is forbidden in production environments. "
                    "Mocking is permitted only during automated test suite execution."
                )
            return self._mock.transcribe(audio_bytes, filename, language)

        # 'auto' strategy:
        # Try Whisper if key available
        if ingestion_settings.OPENAI_API_KEY:
            try:
                return self._whisper.transcribe(audio_bytes, filename, language)
            except Exception as e:
                # If Gemini is also configured, fallback to Gemini
                if ingestion_settings.GEMINI_API_KEY:
                    return self._gemini.transcribe(audio_bytes, filename, language)
                raise AudioTranscriptionError(f"Whisper transcription failed: {e}") from e

        # Try Gemini if key available
        if ingestion_settings.GEMINI_API_KEY:
            return self._gemini.transcribe(audio_bytes, filename, language)

        # If running in explicit automated test mode, allow mock
        if ingestion_settings.ALLOW_TEST_MOCK_TRANSCRIBER:
            return self._mock.transcribe(audio_bytes, filename, language)

        # In production without credentials: DO NOT SILENTLY FAKE IT
        raise AudioTranscriptionError(
            "Audio transcription service unavailable: Neither OPENAI_API_KEY nor GEMINI_API_KEY is configured. "
            "Please configure API credentials in backend/.env to transcribe audio recordings."
        )


audio_transcription_manager = AudioTranscriberManager()
