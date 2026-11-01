"""Small HTTP-based OpenAI/Gemini client; uses existing httpx dependency."""
import json
from typing import Any

import httpx

from .config import settings
from .prompts import SYSTEM_PROMPT, build_user_prompt


class LLMConfigurationError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, provider: str | None = None):
        self.provider = (provider or settings.llm_provider).lower().strip()

    def generate_json(self, text: str, filename: str | None = None,
                      source_type: str | None = None) -> dict[str, Any]:
        if self.provider == "openai":
            return self._openai(text, filename, source_type)
        if self.provider == "gemini":
            return self._gemini(text, filename, source_type)
        raise LLMConfigurationError(
            "LLM_PROVIDER must be either 'openai' or 'gemini'."
        )

    def _openai(self, text: str, filename: str | None,
                source_type: str | None) -> dict[str, Any]:
        if not settings.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not configured.")
        payload = {
            "model": settings.openai_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(text, filename, source_type)},
            ],
        }
        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_json(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            if isinstance(exc, LLMResponseError):
                raise
            raise LLMResponseError(f"OpenAI extraction request failed: {exc}") from exc

    def _gemini(self, text: str, filename: str | None,
                source_type: str | None) -> dict[str, Any]:
        if not settings.gemini_api_key:
            raise LLMConfigurationError("GEMINI_API_KEY is not configured.")
        prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(text, filename, source_type)
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": settings.gemini_api_key},
                json=payload,
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_json(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMResponseError(f"Gemini extraction request failed: {exc}") from exc

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LLMResponseError("LLM returned invalid JSON.") from exc
        if not isinstance(parsed, dict):
            raise LLMResponseError("LLM response must be a JSON object.")
        return parsed
