"""LLM client with auto-detection and fallback chain.

Priority order: groq → openrouter → openai → gemini
If LLM_PROVIDER is explicitly set and the key is present, that provider is used first.
Otherwise, whichever keys are configured are tried in order.
"""
import json
import logging
from typing import Any

import httpx

from .config import settings
from .prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

VALID_PROVIDERS = ("groq", "openrouter", "openai", "gemini")


class LLMConfigurationError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


def _detect_provider() -> str:
    """Return the first provider that has an API key configured."""
    # Honour explicit setting if valid and key is present
    configured = (settings.llm_provider or "").lower().strip()
    if configured in VALID_PROVIDERS:
        key_map = {
            "groq": settings.groq_api_key,
            "openrouter": settings.openrouter_api_key,
            "openai": settings.openai_api_key,
            "gemini": settings.gemini_api_key,
        }
        if key_map.get(configured):
            return configured
        logger.warning(
            "LLM_PROVIDER=%s but key is missing; falling back to auto-detect.", configured
        )

    # Auto-detect: use whichever key is available
    if settings.groq_api_key:
        return "groq"
    if settings.openrouter_api_key:
        return "openrouter"
    if settings.openai_api_key:
        return "openai"
    if settings.gemini_api_key:
        return "gemini"

    raise LLMConfigurationError(
        "No LLM API key is configured. "
        "Set at least one of: GROQ_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY."
    )


class LLMClient:
    def __init__(self, provider: str | None = None):
        self._provider = provider.lower().strip() if provider else None

    @property
    def provider(self) -> str:
        if self._provider and self._provider in VALID_PROVIDERS:
            return self._provider
        return _detect_provider()

    @provider.setter
    def provider(self, value: str | None) -> None:
        self._provider = value.lower().strip() if value else None

    def generate_json(
        self, text: str, filename: str | None = None, source_type: str | None = None
    ) -> dict[str, Any]:
        resolved = self.provider
        logger.info("Using LLM provider: %s", resolved)
        if resolved == "groq":
            return self._groq(text, filename, source_type)
        if resolved == "openrouter":
            return self._openrouter(text, filename, source_type)
        if resolved == "openai":
            return self._openai(text, filename, source_type)
        if resolved == "gemini":
            return self._gemini(text, filename, source_type)
        raise LLMConfigurationError(
            f"Unknown provider '{resolved}'. Must be one of: {', '.join(VALID_PROVIDERS)}."
        )

    # ------------------------------------------------------------------ #
    # Provider implementations
    # ------------------------------------------------------------------ #

    def _groq(self, text: str, filename: str | None, source_type: str | None) -> dict[str, Any]:
        if not settings.groq_api_key:
            raise LLMConfigurationError("GROQ_API_KEY is not configured.")
        model = settings.groq_model or "llama-3.3-70b-versatile"
        payload = {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(text, filename, source_type)},
            ],
        }
        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json=payload,
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            return self._extract_openai_content(response.json(), "Groq")
        except LLMResponseError:
            raise
        except httpx.HTTPStatusError as exc:
            raise LLMResponseError(
                f"Groq API error {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMResponseError(f"Groq request failed: {exc}") from exc

    def _openrouter(
        self, text: str, filename: str | None, source_type: str | None
    ) -> dict[str, Any]:
        if not settings.openrouter_api_key:
            raise LLMConfigurationError("OPENROUTER_API_KEY is not configured.")
        model = settings.openrouter_model or "openai/gpt-4o-mini"
        payload = {
            "model": model,
            "temperature": 0,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(text, filename, source_type)},
            ],
        }
        try:
            response = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://aftermind.app",
                    "X-Title": "AFTERMIND",
                },
                json=payload,
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            resp_json = response.json()
            # OpenRouter may embed an error object even on 200
            if "error" in resp_json:
                err = resp_json["error"]
                raise LLMResponseError(
                    f"OpenRouter error {err.get('code', '')}: {err.get('message', err)}"
                )
            return self._extract_openai_content(resp_json, "OpenRouter")
        except LLMResponseError:
            raise
        except httpx.HTTPStatusError as exc:
            raise LLMResponseError(
                f"OpenRouter API error {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMResponseError(f"OpenRouter request failed: {exc}") from exc

    def _openai(self, text: str, filename: str | None, source_type: str | None) -> dict[str, Any]:
        if not settings.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not configured.")
        model = settings.openai_model or "gpt-4o-mini"
        payload = {
            "model": model,
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
            return self._extract_openai_content(response.json(), "OpenAI")
        except LLMResponseError:
            raise
        except httpx.HTTPStatusError as exc:
            raise LLMResponseError(
                f"OpenAI API error {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMResponseError(f"OpenAI request failed: {exc}") from exc

    def _gemini(self, text: str, filename: str | None, source_type: str | None) -> dict[str, Any]:
        if not settings.gemini_api_key:
            raise LLMConfigurationError("GEMINI_API_KEY is not configured.")
        model = settings.gemini_model or "gemini-2.0-flash"
        prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(text, filename, source_type)
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
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
            resp_json = response.json()
            candidates = resp_json.get("candidates", [])
            if not candidates:
                feedback = resp_json.get("promptFeedback", {})
                block_reason = feedback.get("blockReason", "unknown")
                raise LLMResponseError(
                    f"Gemini returned no candidates (blockReason={block_reason}). "
                    "Try shortening the input."
                )
            candidate = candidates[0]
            finish_reason = candidate.get("finishReason", "")
            parts = candidate.get("content", {}).get("parts", [])
            if not parts or not (parts[0].get("text") or "").strip():
                raise LLMResponseError(
                    f"Gemini returned empty content (finishReason={finish_reason}). "
                    "The model may have been blocked by safety filters."
                )
            return self._parse_json(parts[0]["text"])
        except LLMResponseError:
            raise
        except httpx.HTTPStatusError as exc:
            raise LLMResponseError(
                f"Gemini API error {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMResponseError(f"Gemini request failed: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_openai_content(resp_json: dict, provider_name: str) -> dict[str, Any]:
        """Parse OpenAI-compatible chat completion JSON (used by Groq, OpenRouter, OpenAI)."""
        choices = resp_json.get("choices", [])
        if not choices:
            raise LLMResponseError(
                f"{provider_name} returned no choices. "
                "The request may have been blocked or the model is unavailable."
            )
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            finish_reason = choices[0].get("finish_reason", "unknown")
            raise LLMResponseError(
                f"{provider_name} returned empty content (finish_reason={finish_reason}). "
                "The model output was filtered or truncated."
            )
        return LLMClient._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        # Strip markdown code fences if model wraps JSON in ```json ... ```
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            # Remove first and last fence lines
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            stripped = "\n".join(inner).strip()
        try:
            parsed = json.loads(stripped)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LLMResponseError(
                f"LLM returned invalid JSON. Raw content (first 200 chars): {content[:200]!r}"
            ) from exc
        if not isinstance(parsed, dict):
            raise LLMResponseError("LLM response must be a JSON object, not a list or primitive.")
        return parsed
