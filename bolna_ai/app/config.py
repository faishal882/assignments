from functools import lru_cache

from pydantic import model_validator
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
    processing_claim_timeout_seconds: int = 60
    transcript_max_chars: int = 3000

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        missing = []
        if not self.slack_bot_token:
            missing.append("SLACK_BOT_TOKEN")
        if not self.slack_channel_id:
            missing.append("SLACK_CHANNEL_ID")
        if not self.bolna_webhook_secret:
            missing.append("BOLNA_WEBHOOK_SECRET")
        if self.slack_max_retries < 1:
            raise ValueError("SLACK_MAX_RETRIES must be at least 1")
        if self.processing_claim_timeout_seconds < 1:
            raise ValueError("PROCESSING_CLAIM_TIMEOUT_SECONDS must be at least 1")
        if self.transcript_max_chars < 1:
            raise ValueError("TRANSCRIPT_MAX_CHARS must be at least 1")
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
