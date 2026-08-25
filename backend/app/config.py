from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from the environment.

    Locally the values come from backend/.env; on Vercel they come from the
    project's environment variables. Nothing here has a secret as default.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Empty by default so the app still boots (and /api/health can explain why)
    # when the database is not configured yet.
    database_url: str = ""
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
