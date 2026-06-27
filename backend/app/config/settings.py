"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Aurora TIA"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"

    # Database
    database_backend: Literal["postgresql", "firestore"] = "postgresql"
    database_url: str = Field(
        default="postgresql+asyncpg://aurora:aurora@localhost:5432/aurora_tia"
    )
    database_url_sync: str = Field(
        default="postgresql://aurora:aurora@localhost:5432/aurora_tia"
    )

    # Firebase / Firestore
    firebase_project_id: str = ""
    firebase_credentials_path: str = "./credentials/firebase-service-account.json"
    firestore_emulator_host: str = ""  # e.g. localhost:8080 for local emulator

    # JWT
    jwt_secret_key: str = Field(default="change-me-in-production-use-strong-secret")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # OAuth Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_vision_model: str = "gemini-2.0-flash"

    # Celery / Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Storage
    storage_backend: Literal["local", "supabase"] = "local"
    local_storage_path: str = "./storage"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "aurora-documents"

    # Gmail
    gmail_credentials_path: str = "./credentials/gmail_credentials.json"
    gmail_token_path: str = "./credentials/gmail_token.json"
    gmail_user_email: str = ""

    # Business rules
    confidence_auto_approve_threshold: float = 90.0
    trust_auto_approve_threshold: float = 80.0
    manual_review_trust_threshold: float = 60.0

    # Analytics
    manual_invoice_processing_minutes: float = 15.0
    hourly_labor_cost_usd: float = 45.0
    license_cost_monthly_usd: float = 5000.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
