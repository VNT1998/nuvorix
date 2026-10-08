from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Nuvorix Control Plane"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./nuvorix.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # MLflow
    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"
    
    # Security & RBAC
    AUTH_MODE: str = "development"  # "development" (allows dev headers) or "production" (enforces token validation)
    AUTH_ENABLED: bool = True
    DEFAULT_ORG_ID: str = "org-demo-nuvorix"
    DEFAULT_USER_ID: str = "usr-demo-admin"
    DEFAULT_USER_ROLE: str = "admin"
    SECRET_KEY: str = "nuvorix-insecure-dev-secret-key-change-in-production"
    
    # Observability
    PROMETHEUS_ENABLED: bool = True
    OTEL_ENDPOINT: str = "http://localhost:4317"
    
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


settings = Settings()

# Ensure local directories exist
Path(settings.ARTIFACT_STORE_PATH).mkdir(parents=True, exist_ok=True)
Path("./mlruns").mkdir(parents=True, exist_ok=True)
