from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    port: int = 4000
    api_prefix: str = "/api/v1"
    web_origin: str = "http://localhost:3000,http://127.0.0.1:3000"
    json_body_limit_mb: int = 1
    text_max_length: int = 10_000
    image_max_mb: int = 15
    upload_max_mb: int = 150

    database_url: str | None = None
    migration_database_url: str | None = None
    supabase_url: str | None = None
    supabase_secret_key: str | None = None
    supabase_storage_bucket: str = "analysis-inputs"
    local_upload_dir: Path = Path(".data/uploads")

    @field_validator(
        "database_url",
        "migration_database_url",
        "supabase_url",
        "supabase_secret_key",
        mode="before",
    )
    @classmethod
    def clean_optional_secret(cls, value: str | None) -> str | None:
        if not isinstance(value, str):
            return value
        cleaned = value.strip().strip("'\"")
        environment_names = (
            "DATABASE_URL",
            "MIGRATION_DATABASE_URL",
            "SUPABASE_URL",
            "SUPABASE_SECRET_KEY",
        )
        for env_name in environment_names:
            prefix = f"{env_name}="
            if cleaned.startswith(prefix):
                cleaned = cleaned.removeprefix(prefix).strip().strip("'\"")
        return cleaned or None

    @property
    def web_origins(self) -> list[str]:
        return [origin.strip() for origin in self.web_origin.split(",") if origin.strip()]

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url and self.database_url.strip())

    @property
    def alembic_database_url(self) -> str | None:
        return self.migration_database_url or self.database_url

    @property
    def supabase_storage_configured(self) -> bool:
        return bool(
            self.supabase_url
            and self.supabase_url.strip()
            and self.supabase_secret_key
            and self.supabase_secret_key.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
