from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_NAME: str = "Smart Question Bank"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:3000"

    DATABASE_URL: str = "postgresql+psycopg://sqb_user:change_me_postgres_password@postgres:5432/smart_question_bank"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_CHUNKS: str = "document_chunks"
    QDRANT_COLLECTION_QUESTIONS: str = "question_vectors"

    JWT_SECRET_KEY: str = Field(default="dev-only-insecure-access-secret-override-in-env-32bytes")
    JWT_REFRESH_SECRET_KEY: str = Field(default="dev-only-insecure-refresh-secret-override-in-env-32b")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    INITIAL_ADMIN_EMAIL: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""
    INITIAL_ADMIN_NAME: str = "System Admin"

    # AI Provider Abstraction
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    GENERATION_MODEL: str = "gpt-4.1"
    GENERATION_TEMPERATURE: float = 0.4
    VERIFICATION_MODEL: str = "gpt-4.1"
    VERIFICATION_TEMPERATURE: float = 0.1

    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    BGE_M3_MODEL: str = "BAAI/bge-m3"

    # Document & OCR
    STORAGE_DIR: str = "/app/storage"
    MAX_UPLOAD_SIZE_MB: int = 25
    OCR_LANGUAGES: str = "ben+eng"
    OCR_QUALITY_THRESHOLD: float = 0.70

    # Written Evaluation Rubric (total = 100)
    WRITTEN_RUBRIC_ACCURACY: int = 30
    WRITTEN_RUBRIC_RELEVANCE: int = 20
    WRITTEN_RUBRIC_STRUCTURE: int = 20
    WRITTEN_RUBRIC_CLARITY: int = 15
    WRITTEN_RUBRIC_COMPLETENESS: int = 15

    @field_validator("APP_ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        return v.strip().lower()

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_production_secrets(self) -> None:
        if self.APP_ENV == "production":
            if "change_me" in self.JWT_SECRET_KEY or "dev-only" in self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32:
                raise RuntimeError("JWT_SECRET_KEY must be set to a strong >=32 char secret in production.")
            if (
                "change_me" in self.JWT_REFRESH_SECRET_KEY
                or "dev-only" in self.JWT_REFRESH_SECRET_KEY
                or len(self.JWT_REFRESH_SECRET_KEY) < 32
            ):
                raise RuntimeError("JWT_REFRESH_SECRET_KEY must be set to a strong >=32 char secret in production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
