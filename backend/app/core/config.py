from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BLANK_TO_NONE_FIELDS = ("admin_email", "admin_password", "sentry_dsn", "openai_api_key", "anthropic_api_key", "gemini_api_key", "languagetool_url")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./academic_writer.db"

    jwt_secret_key: str = "change-me-to-a-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    admin_email: str | None = None
    admin_password: str | None = None

    sentry_dsn: str | None = None

    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-5"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Self-hosted LanguageTool server URL (e.g. http://localhost:8010/). Falls back to
    # languagetool.org's rate-limited public API when unset.
    languagetool_url: str | None = None

    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator(*_BLANK_TO_NONE_FIELDS, mode="before")
    @classmethod
    def _blank_string_means_unset(cls, value: str | None) -> str | None:
        # An explicitly blank `.env` value (e.g. `ANTHROPIC_API_KEY=`) must behave the
        # same as an unset one — provider SDKs treat api_key="" as "use this literal
        # empty string" rather than "fall back to auto-detection", which fails oddly.
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
