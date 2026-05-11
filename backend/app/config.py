"""Centralised settings, loaded from environment with pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_embed_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBED_MODEL"
    )
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(
        default="llama-3.1-70b-versatile", alias="GROQ_MODEL"
    )

    # Server
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    cors_origins: str = Field(
        default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Supabase
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_service_key: str | None = Field(
        default=None, alias="SUPABASE_SERVICE_KEY"
    )

    # Storage
    chroma_persist_dir: str = Field(
        default="./data/chroma", alias="CHROMA_PERSIST_DIR"
    )
    upload_dir: str = Field(default="./data/uploads", alias="UPLOAD_DIR")
    max_upload_mb: int = Field(default=20, alias="MAX_UPLOAD_MB")

    # Rate limiting
    rate_limit_per_min: int = Field(default=30, alias="RATE_LIMIT_PER_MIN")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
