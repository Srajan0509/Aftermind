from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TrackerSettings(BaseSettings):
    """Configuration for AFTERMIND Module 4 (override with TRACKER_* environment variables)."""

    # A commitment due within this many days (and not overdue) is flagged "due_soon".
    due_soon_days: int = Field(default=3, ge=0, le=60)
    # Default look-ahead window for /upcoming.
    default_upcoming_days: int = Field(default=7, ge=1, le=365)
    # Upper bound of rows read from Module 3 per status.
    max_rows: int = Field(default=10_000, ge=1)

    model_config = SettingsConfigDict(
        env_prefix="TRACKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


tracker_settings = TrackerSettings()
