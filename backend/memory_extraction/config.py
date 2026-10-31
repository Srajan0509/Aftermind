"""Environment-based configuration for Module 2."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractionSettings(BaseSettings):
    llm_provider: str = "openai"  # openai | gemini
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    llm_timeout_seconds: float = 45.0
    max_input_characters: int = 100_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = ExtractionSettings()
