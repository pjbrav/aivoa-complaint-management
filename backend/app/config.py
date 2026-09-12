"""
Central application configuration.

All secrets and environment-dependent values are read from environment
variables (via a local .env file in development). Nothing here is
hardcoded so the same code can run in dev/stage/prod by swapping env vars.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Groq / LLM
    groq_api_key: str = ""
    groq_primary_model: str = "gemma2-9b-it"
    groq_secondary_model: str = "llama-3.3-70b-versatile"

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/aivoa_complaints"

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    max_upload_mb: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
