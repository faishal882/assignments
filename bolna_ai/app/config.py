from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    slack_bot_token: str = ""
    slack_channel_id: str = ""
    bolna_webhook_secret: str = ""
    bolna_api_key: str = ""
    bolna_api_base_url: str = "https://api.bolna.ai"
    sqlite_path: str = "alerts.db"
    slack_max_retries: int = 3
    slack_retry_backoff_seconds: float = 0.5
    transcript_max_chars: int = 3000


@lru_cache
def get_settings() -> Settings:
    return Settings()
