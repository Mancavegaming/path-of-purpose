"""Server configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All config comes from env vars or .env file."""

    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    ai_provider: str = "gemini"

    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_guild_id: str = "1463950138430193758"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    jwt_secret: str = ""
    jwt_expiry_hours: int = 168  # 7 days

    server_host: str = "0.0.0.0"
    server_port: int = 8080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
