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

    # LLM Providers & Inference
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LOCAL_LLM_URL: str = "http://localhost:11434/v1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_PRIMARY_MODEL: str = "medgemma:4b"
    OLLAMA_FALLBACK_MODELS: list[str] = ["qwen2.5:3b", "llama3.2:3b"]

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
        is_prod = self.ENVIRONMENT.lower() == "production"

        if is_prod:
            if self.AUTH_MODE != "production":
                raise ValueError(
                    "Production configuration error: ENVIRONMENT='production' requires AUTH_MODE='production'."
                )
            if not self.AUTH_ENABLED:
                raise ValueError(
                    "Production configuration error: ENVIRONMENT='production' requires AUTH_ENABLED=True."
                )
            if (
                not self.SECRET_KEY
                or self.SECRET_KEY == "nuvorix-insecure-dev-secret-key-change-in-production"
                or "insecure" in self.SECRET_KEY.lower()
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError(
                    "Production configuration error: ENVIRONMENT='production' requires an externally configured, "
                    "cryptographically secure SECRET_KEY with at least 32 characters."
                )
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "Production configuration error: ENVIRONMENT='production' requires PostgreSQL database (DATABASE_URL), SQLite is forbidden."
                )
            if (
                not self.MLFLOW_TRACKING_URI
                or self.MLFLOW_TRACKING_URI.startswith("sqlite")
                or "localhost" in self.MLFLOW_TRACKING_URI
            ):
                raise ValueError(
                    "Production configuration error: ENVIRONMENT='production' requires an external MLflow tracking URI (not local SQLite or localhost)."
                )
            if not self.CORS_ORIGINS or any(
                "localhost" in origin or "127.0.0.1" in origin for origin in self.CORS_ORIGINS
            ):
                raise ValueError(
                    "Production configuration error: ENVIRONMENT='production' requires explicit non-localhost CORS_ORIGINS."
                )

        elif self.AUTH_MODE == "production":
            if (
                not self.SECRET_KEY
                or self.SECRET_KEY == "nuvorix-insecure-dev-secret-key-change-in-production"
                or "insecure" in self.SECRET_KEY.lower()
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError(
                    "Configuration error: AUTH_MODE='production' requires an externally configured, "
                    "cryptographically secure SECRET_KEY with at least 32 characters."
                )

        return self


settings = Settings()

# Ensure local directories exist
Path(settings.ARTIFACT_STORE_PATH).mkdir(parents=True, exist_ok=True)
Path("./mlruns").mkdir(parents=True, exist_ok=True)
