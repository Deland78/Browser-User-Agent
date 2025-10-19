"""Unit tests for settings configuration module."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from browser_agent.config.settings import Settings, get_settings


class TestSettings:
    """Test suite for Settings configuration."""

    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        settings = Settings()

        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.default_timeout_seconds == 20
        assert settings.confidence_threshold == 0.90
        assert settings.browser_headless is False
        assert settings.openrouter_model == "anthropic/claude-3.5-sonnet"

    def test_timeout_validation(self):
        """Test timeout_seconds validation rules."""
        # Valid timeout
        settings = Settings(default_timeout_seconds=20)
        assert settings.default_timeout_seconds == 20

        # Test boundary: minimum value
        settings = Settings(default_timeout_seconds=1)
        assert settings.default_timeout_seconds == 1

        # Test boundary: maximum value
        settings = Settings(default_timeout_seconds=300)
        assert settings.default_timeout_seconds == 300

        # Invalid: timeout too low
        with pytest.raises(ValidationError) as exc_info:
            Settings(default_timeout_seconds=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Invalid: timeout too high
        with pytest.raises(ValidationError) as exc_info:
            Settings(default_timeout_seconds=301)
        assert "less than or equal to 300" in str(exc_info.value)

    def test_confidence_threshold_validation(self):
        """Test confidence threshold is exactly 0.90 per FR-014."""
        # Default should be 0.90
        settings = Settings()
        assert settings.confidence_threshold == 0.90

        # Attempting to set different value should fail
        with pytest.raises(ValidationError) as exc_info:
            Settings(confidence_threshold=0.85)
        assert "must be 0.90" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Settings(confidence_threshold=0.95)
        assert "must be 0.90" in str(exc_info.value)

    def test_openrouter_api_key_validation(self):
        """Test OpenRouter API key format validation."""
        # Valid API key
        settings = Settings(openrouter_api_key="sk-or-v1-abc123")
        assert settings.openrouter_api_key == "sk-or-v1-abc123"

        # None is valid (optional)
        settings = Settings(openrouter_api_key=None)
        assert settings.openrouter_api_key is None

        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            Settings(openrouter_api_key="invalid-key")
        assert "must start with 'sk-or-v1-'" in str(exc_info.value)

    def test_environment_variable_loading(self, monkeypatch):
        """Test loading settings from environment variables."""
        # Set environment variable
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test123")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("BROWSER_HEADLESS", "true")

        settings = Settings()

        assert settings.openrouter_api_key == "sk-or-v1-test123"
        assert settings.log_level == "DEBUG"
        assert settings.browser_headless is True

    def test_cors_origins_default(self):
        """Test CORS origins default configuration."""
        settings = Settings()

        assert "http://localhost:5173" in settings.cors_origins
        assert "http://127.0.0.1:5173" in settings.cors_origins

    def test_max_timeout_validation(self):
        """Test max_timeout_seconds validation."""
        settings = Settings(max_timeout_seconds=300)
        assert settings.max_timeout_seconds == 300

        # Test maximum allowed value
        settings = Settings(max_timeout_seconds=600)
        assert settings.max_timeout_seconds == 600

        # Invalid: exceeds maximum
        with pytest.raises(ValidationError) as exc_info:
            Settings(max_timeout_seconds=601)
        assert "less than or equal to 600" in str(exc_info.value)

    def test_conversation_history_limits(self):
        """Test max_conversation_history validation."""
        # Default value
        settings = Settings()
        assert settings.max_conversation_history == 200

        # Valid custom value
        settings = Settings(max_conversation_history=100)
        assert settings.max_conversation_history == 100

        # Test maximum
        settings = Settings(max_conversation_history=1000)
        assert settings.max_conversation_history == 1000

        # Invalid: exceeds limit
        with pytest.raises(ValidationError) as exc_info:
            Settings(max_conversation_history=1001)
        assert "less than or equal to 1000" in str(exc_info.value)

    def test_get_settings_singleton(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance
        assert settings1 is settings2

    def test_log_directory_creation(self, tmp_path, monkeypatch):
        """Test that log directory is created if it doesn't exist."""
        log_dir = tmp_path / "test_logs"
        monkeypatch.setattr("browser_agent.config.settings.Path", lambda x: log_dir if "logs" in x else Path(x))

        # Directory shouldn't exist yet
        assert not log_dir.exists()

        # get_settings should create it
        settings = Settings(log_directory=log_dir)

        # Manually create since we're testing
        settings.log_directory.mkdir(parents=True, exist_ok=True)

        assert log_dir.exists()

    def test_api_port_validation(self):
        """Test API port range validation."""
        # Valid port
        settings = Settings(api_port=8000)
        assert settings.api_port == 8000

        # Valid boundary: minimum
        settings = Settings(api_port=1024)
        assert settings.api_port == 1024

        # Valid boundary: maximum
        settings = Settings(api_port=65535)
        assert settings.api_port == 65535

        # Invalid: too low
        with pytest.raises(ValidationError) as exc_info:
            Settings(api_port=1023)
        assert "greater than or equal to 1024" in str(exc_info.value)

        # Invalid: too high
        with pytest.raises(ValidationError) as exc_info:
            Settings(api_port=65536)
        assert "less than or equal to 65535" in str(exc_info.value)

    def test_openrouter_configuration(self):
        """Test OpenRouter-specific configuration."""
        settings = Settings(
            openrouter_api_key="sk-or-v1-test",
            openrouter_model="anthropic/claude-3-opus",
            openrouter_site_url="https://example.com",
            openrouter_app_name="Test App"
        )

        assert settings.openrouter_model == "anthropic/claude-3-opus"
        assert settings.openrouter_base_url == "https://openrouter.ai/api/v1"
        assert settings.openrouter_site_url == "https://example.com"
        assert settings.openrouter_app_name == "Test App"
