from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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

    # Absolute base of the deployed app, used to build the magic-link URL.
    app_base_url: str = "http://localhost:5173"

    # The only addresses allowed to sign in. Anything else is silently ignored:
    # see api/auth.py for why the response must not reveal the difference.
    #
    # NoDecode is load-bearing: without it pydantic-settings tries to read the
    # env var as JSON before any validator runs, and a comma-separated list
    # blows up at parse time rather than reaching split_emails below.
    allowed_emails: Annotated[list[str], NoDecode] = []

    # Brevo. When the key is missing the sender falls back to printing the link
    # on the console, which is what makes local development bearable.
    brevo_api_key: str = ""
    mail_from: str = ""
    mail_from_name: str = "Wallet"

    login_token_ttl_minutes: int = 15
    session_ttl_days: int = 30
    login_requests_per_hour: int = 20

    @field_validator("allowed_emails", mode="before")
    @classmethod
    def split_emails(cls, value: object) -> object:
        """Accept a comma-separated string, since that is all an env var can carry."""
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
