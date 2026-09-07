"""Unit tests for backend configuration."""

from backend.app.config import Settings


def test_default_settings() -> None:
    """Verify default settings values."""
    settings = Settings()
    assert settings.backend_host == "127.0.0.1"
    assert settings.backend_port == 8000
    assert settings.service_name == "ForecastGuard API"
    assert settings.version == "1.0.0"
    assert settings.api_v1_prefix == "/api/v1"
    assert "http://localhost:5173" in settings.cors_origins


def test_cors_origins_string_parsing() -> None:
    """Verify CORS origins string is parsed into a list."""
    settings = Settings(cors_origins="http://example.com, http://test.com")
    assert settings.cors_origins == ["http://example.com", "http://test.com"]
