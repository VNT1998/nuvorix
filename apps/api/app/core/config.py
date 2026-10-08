from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Nuvorix Control Plane"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./nuvorix.db"
    
    ENVIRONMENT: str = "development"
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # MLflow
    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"
    MLFLOW_BACKEND_STORE_URI: str | None = None
    MLFLOW_ARTIFACT_ROOT: str | None = None
    
    # Security & RBAC
    AUTH_MODE: str = "development"  # "development" (allows dev headers) or "production" (enforces token validation)
    AUTH_ENABLED: bool = True
    DEFAULT_ORG_ID: str = "org-demo-nuvorix"
    DEFAULT_USER_ID: str = "dev-demo-user"
    DEFAULT_USER_ROLE: str = "developer"
    SECRET_KEY: str = "nuvorix-insecure-dev-secret-key-change-in-production"
    API_KEY_PREFIX: str = "nvx_"
    
    # Observability
    PROMETHEUS_ENABLED: bool = True
    OTEL_ENABLED: bool = True
    OTEL_ENDPOINT: str = "http://localhost:4317"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    
    # Artifacts & Local Storage
    ARTIFACT_STORE_PATH: str = "./artifacts"
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.AUTH_MODE == "production" and (
            not self.SECRET_KEY
            or self.SECRET_KEY == "nuvorix-insecure-dev-secret-key-change-in-production"
            or "insecure" in self.SECRET_KEY.lower()
            or len(self.SECRET_KEY) < 32
        ):
            raise ValueError(
                "Production configuration error: AUTH_MODE='production' requires an externally configured, "
                "cryptographically secure SECRET_KEY with at least 32 characters."
            )
        return self


settings = Settings()

# Ensure local directories exist
Path(settings.ARTIFACT_STORE_PATH).mkdir(parents=True, exist_ok=True)
Path("./mlruns").mkdir(parents=True, exist_ok=True)
