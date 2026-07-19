from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Payout Management API"
    environment: str = "development"
    database_url: str = Field(
        default="postgresql+asyncpg://payout:payout@localhost:5432/payouts"
    )
    internal_api_key: str = "development-only-key"
    advance_job_enabled: bool = True
    advance_job_cron: str = "*/5 * * * *"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
