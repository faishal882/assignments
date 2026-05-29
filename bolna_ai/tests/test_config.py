import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_require_runtime_secrets():
    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "Missing required settings" in str(exc_info.value)


def test_settings_reject_invalid_numeric_values():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            slack_bot_token="token",
            slack_channel_id="C123",
            bolna_webhook_secret="secret",
            slack_max_retries=0,
        )

    assert "SLACK_MAX_RETRIES must be at least 1" in str(exc_info.value)
