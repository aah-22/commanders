"""Settings from the environment (Coolify) or a local .env; every value has a safe default for tests."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    season: int = 2026
    team: str = "WAS"
    database_url_ro: str = "sqlite:///./dev.db"  # the API only ever gets the read-only role's URL
    cors_origins: str = "https://commanders.caabi.dev,http://localhost:4200"
    cache_ttl_s: int = 300
    rate_limit: str = "120/minute"
    log_level: str = "INFO"

    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
