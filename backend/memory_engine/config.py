import os
from typing import List, Optional
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
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "auto")  # 'auto', 'gemini', 'openai', 'local'
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")  # 'auto', 'gemini', 'openai', 'heuristic'
    
    # Security & CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )


memory_config = MemoryEngineConfig()
