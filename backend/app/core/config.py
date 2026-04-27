from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    DATABASE_URL: str = Field(..., min_length=1)
    REDIS_URL: str = Field(..., min_length=1)
    JWT_SECRET: str = Field(..., min_length=1)
    ENCRYPTION_KEY: str = Field(..., min_length=1)
    CSRF_SECRET: str = Field(..., min_length=1)
    MINIO_ROOT_USER: str = Field(..., min_length=1)
    MINIO_ROOT_PASSWORD: str = Field(..., min_length=1)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    NLP_SERVICE_URL: str = "http://localhost:8001"


settings = Settings()
