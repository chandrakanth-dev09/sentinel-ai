from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_NAME: str = "SentinelAI"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = (
        "postgresql+psycopg://sentinelai:"
        "REPLACE_WITH_LOCAL_PASSWORD@localhost:5432/sentinelai"
    )
    CORS_ORIGINS: str = "http://localhost:5173"
    MAX_INGEST_BATCH_SIZE: int = 500
    MAX_FUTURE_TIMESTAMP_SKEW_SECONDS: int = 300
    MODEL_PATH: str = "backend/models/isolation_forest.joblib"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
