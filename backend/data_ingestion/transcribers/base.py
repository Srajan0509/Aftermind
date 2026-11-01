from abc import ABC, abstractmethod
from typing import Optional
from ..schemas import AudioTranscribeResult


class AudioTranscriptionError(Exception):
    """Raised when audio transcription fails or audio format is invalid."""
    pass


class BaseAudioTranscriber(ABC):
    """Abstract base class for audio transcription providers."""

    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> AudioTranscribeResult:
        """
        Transcribes audio bytes into standardized transcript text.

        :param audio_bytes: Raw binary audio
        :param filename: Audio file name (e.g. voice_note.mp3)
        :param language: Optional ISO-639-1 language code (e.g. 'en')
        :return: AudioTranscribeResult
        :raises AudioTranscriptionError: on transcription or network failure
        """
        pass

