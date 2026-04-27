from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    MODEL_NAME: str = Field(default="DeepPavlov/rubert-base-cased", min_length=1)
    MODEL_CACHE_DIR: str = Field(..., min_length=1)
    MAX_TEXT_LENGTH: int = Field(default=4000, gt=0)
    BATCH_SIZE: int = Field(default=8, gt=0)


settings = Settings()
