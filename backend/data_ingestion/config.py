import os
from typing import Set
from pydantic_settings import BaseSettings


class IngestionSettings(BaseSettings):
    """Configuration for Module 1: Multi-Source AI Data Ingestion."""

    # Provider for audio transcription: 'auto', 'whisper', 'gemini'
    AUDIO_TRANSCRIBER_PROVIDER: str = "auto"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_WHISPER_MODEL: str = "whisper-1"
    GEMINI_AUDIO_MODEL: str = "gemini-1.5-flash"

    # Testing flag: Mock transcription permitted ONLY for automated tests
    ALLOW_TEST_MOCK_TRANSCRIBER: bool = False

    # Input limits
    MAX_DOCUMENT_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    MAX_AUDIO_SIZE_BYTES: int = 50 * 1024 * 1024     # 50 MB
    MAX_TEXT_CHARACTERS: int = 100000                 # Matches Module 2 threshold

    # The 6 strictly requested core formats:
    SUPPORTED_DOCUMENT_EXTENSIONS: Set[str] = {
        ".pdf",
        ".docx",
        ".txt",
    }

    SUPPORTED_AUDIO_EXTENSIONS: Set[str] = {
        ".mp3",
        ".wav",
        ".m4a",
    }

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


ingestion_settings = IngestionSettings(
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
    GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
    AUDIO_TRANSCRIBER_PROVIDER=os.getenv("AUDIO_TRANSCRIBER_PROVIDER", "auto"),
    ALLOW_TEST_MOCK_TRANSCRIBER=os.getenv("ALLOW_TEST_MOCK_TRANSCRIBER", "false").lower() in ("true", "1", "yes"),
)
