"""Application configuration using Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    level: str = Field("INFO", validation_alias="LOG_LEVEL")
    json: bool = Field(True, validation_alias="LOG_JSON")


class MetricsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    enabled: bool = Field(True, validation_alias="METRICS_ENABLED")
    endpoint: str = Field("/metrics", validation_alias="METRICS_ENDPOINT")


class TracingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    enabled: bool = Field(False, validation_alias="OTEL_ENABLED")
    endpoint: Optional[str] = Field(None, validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    service_name: str = Field("dubai-real-estate-api", validation_alias="OTEL_SERVICE_NAME")


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = Field("0.0.0.0", validation_alias="API_HOST")
    port: int = Field(8787, validation_alias="API_PORT")


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    provider: Literal["openai", "gemini"] = Field("gemini", validation_alias="LLM_PROVIDER")
    openai_api_key: Optional[str] = Field(None, validation_alias="OPENAI_API_KEY")
    openai_chat_model: str = Field("gpt-4o-mini", validation_alias="OPENAI_CHAT_MODEL")
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")
    gemini_chat_model: str = Field("gemini-2.0-flash", validation_alias="GEMINI_CHAT_MODEL")

    def validate_keys(self) -> None:
        if self.provider == "gemini" and not self.gemini_api_key:
            msg = "GEMINI_API_KEY must be provided when LLM_PROVIDER=gemini"
            raise ValueError(msg)
        if self.provider == "openai" and not self.openai_api_key:
            msg = "OPENAI_API_KEY must be provided when LLM_PROVIDER=openai"
            raise ValueError(msg)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    neon_db_url: Optional[str] = Field(None, validation_alias="NEON_DB_URL")
    fallback_db_url: Optional[str] = Field(None, validation_alias=AliasChoices("SUPABASE_DB_URL", "FALLBACK_DB_URL"))
    pool_size: int = Field(10, validation_alias="DB_POOL_SIZE")

    @property
    def primary_db_url(self) -> str:
        if self.neon_db_url:
            return self.neon_db_url
        if self.fallback_db_url:
            return self.fallback_db_url
        raise ValueError("No database URL configured (NEON_DB_URL or SUPABASE_DB_URL)")


class NeonRestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    url: str = Field(..., validation_alias=AliasChoices("NEON_REST_URL", "SUPABASE_URL"))
    service_role_key: str = Field(..., validation_alias=AliasChoices("NEON_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY"))


class EmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    model: str = Field("models/text-embedding-004", validation_alias="EMBEDDING_MODEL")
    dimensions: int = Field(1536, validation_alias="EMBEDDING_DIM")


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    enabled: bool = Field(False, validation_alias="AUTH_ENABLED")
    jwt_secret: str = Field("dev-secret-change-me", validation_alias=AliasChoices("NEON_JWT_SECRET", "SUPABASE_JWT_SECRET"))
    jwt_audience: Optional[str] = Field("authenticated", validation_alias="AUTH_JWT_AUDIENCE")
    jwt_algorithms: tuple[str, ...] = Field(("HS256",), validation_alias="AUTH_JWT_ALGORITHMS")
    magic_link_redirect_url: Optional[str] = Field(None, validation_alias="AUTH_MAGIC_LINK_REDIRECT")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    tracing: TracingSettings = Field(default_factory=TracingSettings)
    api: APISettings = Field(default_factory=APISettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    neon_rest: NeonRestSettings = Field(default_factory=NeonRestSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)

    def validate(self) -> None:
        self.llm.validate_keys()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings
