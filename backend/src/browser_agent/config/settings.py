"""Application configuration settings."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(value: str | list[str]) -> list[str]:
    """Parse CORS origins from comma-separated string or list."""
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    return value


class Settings(BaseSettings):
    """Strongly typed runtime configuration."""

    # Application Environment
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    log_directory: Path = Field(default=Path("backend") / "logs")

    # Database Configuration
    database_url: str = Field(default="sqlite+aiosqlite:///backend/browser_agent.db")

    # OpenRouter LLM Configuration
    openrouter_api_key: str | None = Field(default=None, env="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="anthropic/claude-3.5-sonnet")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    openrouter_site_url: str | None = Field(default=None, env="OPENROUTER_SITE_URL")
    openrouter_app_name: str = Field(default="Browser-Agent-Chat")

    # Browser Automation Configuration
    browser_headless: bool = Field(default=False)
    default_timeout_seconds: int = Field(default=20, ge=1, le=300)
    max_timeout_seconds: int = Field(default=300, ge=1, le=600)

    # Chat Configuration
    max_conversation_history: int = Field(default=200, ge=1, le=1000)
    session_timeout_minutes: int = Field(default=60, ge=1, le=1440)

    # Confidence Evaluation (FR-014)
    confidence_threshold: float = Field(default=0.90, ge=0.0, le=1.0)

    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1024, le=65535)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: str | None) -> str | None:
        """Validate OpenRouter API key format if provided."""
        if v and not v.startswith("sk-or-v1-"):
            raise ValueError("OpenRouter API key must start with 'sk-or-v1-'")
        return v

    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        """Ensure confidence threshold is exactly 0.90 per FR-014."""
        if v != 0.90:
            raise ValueError("Confidence threshold must be 0.90 per specification (FR-014)")
        return v

    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Prevent JSON parsing for list fields - we'll handle it in validator
        env_ignore_empty=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings_instance = Settings()
    settings_instance.log_directory.mkdir(parents=True, exist_ok=True)
    return settings_instance


settings = get_settings()

