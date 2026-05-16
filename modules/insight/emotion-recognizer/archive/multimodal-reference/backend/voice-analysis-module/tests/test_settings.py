import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _build_settings_without_env_file(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_settings_use_default_values_when_env_is_empty(monkeypatch):
    for variable in (
        "AZURE_SPEECH_KEY",
        "AZURE_SPEECH_REGION",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "LOG_LEVEL",
        "MAX_UPLOAD_SIZE_MB",
        "AUDIO_CONVERSION_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(variable, raising=False)

    settings = _build_settings_without_env_file()

    assert settings.azure_speech_key is None
    assert settings.openai_model == "gpt-5.4"
    assert settings.log_level == "INFO"
    assert settings.max_upload_size_mb == 25
    assert settings.audio_conversion_timeout_seconds == 30


def test_settings_normalizes_log_level_case(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = _build_settings_without_env_file()

    assert settings.log_level == "DEBUG"


def test_settings_rejects_invalid_log_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "GIBBERISH")

    with pytest.raises(ValidationError):
        _build_settings_without_env_file()


def test_settings_rejects_non_positive_upload_size(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "0")

    with pytest.raises(ValidationError):
        _build_settings_without_env_file()


def test_settings_rejects_non_integer_audio_timeout(monkeypatch):
    monkeypatch.setenv("AUDIO_CONVERSION_TIMEOUT_SECONDS", "abc")

    with pytest.raises(ValidationError):
        _build_settings_without_env_file()


def test_settings_prioritizes_dotenv_over_process_environment(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=from-dotenv\nOPENAI_MODEL=model-from-dotenv\n")
    monkeypatch.setenv("OPENAI_API_KEY", "from-process-env")
    monkeypatch.setenv("OPENAI_MODEL", "model-from-process-env")

    settings = Settings(_env_file=env_file)

    assert settings.openai_api_key == "from-dotenv"
    assert settings.openai_model == "model-from-dotenv"
