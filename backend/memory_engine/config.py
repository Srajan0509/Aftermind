import os
from typing import List, Optional, Union
from pydantic import field_validator
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings
    SettingsConfigDict = None


class MemoryEngineConfig(BaseSettings):
    """Configuration settings for AFTERMIND Module 3: Connected Long-Term Memory & Semantic Search."""
    MODULE_NAME: str = "Connected Long-Term Memory & Semantic Search"
    VERSION: str = "1.0.0"
    
    # Database Configuration
    # Uses PostgreSQL with pgvector in production/Supabase, falls back to SQLite for local standalone development
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aftermind_memory.db")
    
    # Vector Search & Embeddings
    VECTOR_DIMENSION: int = 1536  # Standard embedding dimension (OpenAI / Gemini)
    SIMILARITY_THRESHOLD: float = 0.15  # Minimum cosine similarity for retrieval
    DEFAULT_SEARCH_LIMIT: int = 10
    
    # AI Credentials & Providers
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY", None)
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "auto")  # 'auto', 'gemini', 'openai', 'local'
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")  # 'auto', 'gemini', 'openai', 'groq', 'openrouter', 'heuristic'
    
    # Security & CORS
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def normalize_allowed_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )


memory_config = MemoryEngineConfig()
