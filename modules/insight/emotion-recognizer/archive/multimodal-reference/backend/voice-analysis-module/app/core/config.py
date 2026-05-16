from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]


class Settings(BaseSettings):
    """Configuração da aplicação carregada de variáveis de ambiente e/ou .env.

    A precedência prioriza o `.env` local para preservar o comportamento esperado
    em desenvolvimento, evitando que variáveis globais antigas do sistema sejam
    usadas por engano.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4"
    log_level: LogLevel = "INFO"
    max_upload_size_mb: int = Field(default=25, ge=1)
    audio_conversion_timeout_seconds: int = Field(default=30, ge=1)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


settings = Settings()
