"""Application configuration settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Strongly typed runtime configuration."""

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    log_directory: Path = Field(default=Path("backend") / "logs")
    database_url: str = Field(default="sqlite+aiosqlite:///backend/browser_agent.db")
    openrouter_api_key: str | None = Field(default=None, env="OPENROUTER_API_KEY")
    default_timeout_seconds: int = Field(default=20, ge=1, le=300)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings_instance = Settings()
    settings_instance.log_directory.mkdir(parents=True, exist_ok=True)
    return settings_instance


settings = get_settings()

