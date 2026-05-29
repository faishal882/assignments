from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class BolnaEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    execution_id: str | None = None
    agent_id: str | None = None
    status: str | None = None
    transcript: str | None = None
    conversation_time: float | None = None
    telephony_data: dict[str, Any] | None = None

    @property
    def canonical_execution_id(self) -> str | None:
        return self.execution_id or self.id

    @property
    def duration_seconds(self) -> float | None:
        if self.conversation_time is not None:
            return self.conversation_time
        if self.telephony_data and "duration" in self.telephony_data:
            duration = self.telephony_data["duration"]
            if isinstance(duration, int | float):
                return float(duration)
        return None

    def with_transcript(self, transcript: str | None) -> "BolnaEvent":
        return self.model_copy(update={"transcript": transcript})


class SlackMessage(BaseModel):
    text: str
    blocks: list[dict[str, Any]]


class SlackPostResult(BaseModel):
    channel: str
    ts: str


class AlertRecord(BaseModel):
    execution_id: str
    state: str
    slack_channel: str | None = None
    slack_ts: str | None = None
    transcript_recovered: bool = False


class WebhookResponse(BaseModel):
    status: str
    execution_id: str | None = None
    transcript_recovered: bool = False
    request_id: str | None = None
