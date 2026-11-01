import os
from typing import Optional
import httpx

from .base import BaseAudioTranscriber, AudioTranscriptionError
from ..schemas import AudioTranscribeResult
from ..config import ingestion_settings
from ..normalizer import text_normalizer


class WhisperAudioTranscriber(BaseAudioTranscriber):
    """Transcribes audio using the OpenAI Whisper API via httpx."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or ingestion_settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        self.model = model or ingestion_settings.OPENAI_WHISPER_MODEL

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> AudioTranscribeResult:
        if not self.api_key:
            raise AudioTranscriptionError(
                "OPENAI_API_KEY is not configured for Whisper transcription."
            )

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        mime_types = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "m4a": "audio/mp4",
            "ogg": "audio/ogg",
            "webm": "audio/webm",
            "flac": "audio/flac",
        }
        mime = mime_types.get(ext, "application/octet-stream")

        files = {
            "file": (filename, audio_bytes, mime),
        }
        data = {
            "model": self.model,
            "response_format": "verbose_json",
        }
        if language:
            data["language"] = language

        try:
            response = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files,
                data=data,
                timeout=60.0
            )
        except Exception as e:
            raise AudioTranscriptionError(f"Network error calling OpenAI Whisper API: {e}") from e

        if response.status_code != 200:
            raise AudioTranscriptionError(
                f"OpenAI Whisper API failed ({response.status_code}): {response.text}"
            )

        resp_json = response.json()
        raw_text = resp_json.get("text", "").strip()
        duration = resp_json.get("duration", None)
        detected_language = resp_json.get("language", language)

        cleaned_text, stats = text_normalizer.normalize(raw_text, filename)

        return AudioTranscribeResult(
            filename=filename,
            audio_format=ext,
            duration_seconds=duration,
            language=detected_language,
            transcript=cleaned_text,
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            provider_used="openai_whisper",
            metadata={"model": self.model, "segments_count": len(resp_json.get("segments", []))}
        )

