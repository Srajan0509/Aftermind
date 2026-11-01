import base64
import os
from typing import Optional
import httpx

from .base import BaseAudioTranscriber, AudioTranscriptionError
from ..schemas import AudioTranscribeResult
from ..config import ingestion_settings
from ..normalizer import text_normalizer


class GeminiAudioTranscriber(BaseAudioTranscriber):
    """Transcribes audio using Google Gemini multimodal audio recognition via httpx."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or ingestion_settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.model = model or ingestion_settings.GEMINI_AUDIO_MODEL

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str] = None
    ) -> AudioTranscribeResult:
        if not self.api_key:
            raise AudioTranscriptionError(
                "GEMINI_API_KEY is not configured for Gemini audio transcription."
            )

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        mime_types = {
            "mp3": "audio/mp3",
            "wav": "audio/wav",
            "m4a": "audio/m4a",
            "ogg": "audio/ogg",
            "webm": "audio/webm",
            "flac": "audio/flac",
        }
        mime = mime_types.get(ext, "audio/mp3")
        b64_data = base64.b64encode(audio_bytes).decode("ascii")

        prompt = (
            "You are an expert audio transcription system. "
            "Transcribe the following audio recording accurately into clear, verbatim text. "
            "Do not include commentary, notes, or introductions—only the transcribed speech."
        )
        if language:
            prompt += f" The audio is in {language}."

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime,
                                "data": b64_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0
            }
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        try:
            response = httpx.post(url, json=payload, timeout=60.0)
        except Exception as e:
            raise AudioTranscriptionError(f"Network error calling Gemini Audio API: {e}") from e

        if response.status_code != 200:
            raise AudioTranscriptionError(
                f"Gemini Audio API failed ({response.status_code}): {response.text}"
            )

        resp_json = response.json()
        raw_text = ""
        candidates = resp_json.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                raw_text = parts[0].get("text", "").strip()

        if not raw_text:
            raise AudioTranscriptionError(f"Gemini returned empty transcription for {filename}.")

        cleaned_text, stats = text_normalizer.normalize(raw_text, filename)

        return AudioTranscribeResult(
            filename=filename,
            audio_format=ext,
            duration_seconds=None,
            language=language,
            transcript=cleaned_text,
            character_count=stats["character_count"],
            word_count=stats["word_count"],
            provider_used="gemini_audio",
            metadata={"model": self.model}
        )
