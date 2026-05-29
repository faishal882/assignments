from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.models import BolnaEvent, SlackMessage, SlackPostResult


class SlackApiError(RuntimeError):
    pass


@dataclass
class SlackPublisher:
    bot_token: str
    default_channel: str
    transcript_max_chars: int
    timeout_seconds: float = 10.0

    def build_message(self, event: BolnaEvent) -> SlackMessage:
        execution_id = event.canonical_execution_id or "unknown"
        agent_id = event.agent_id or "unknown"
        duration = (
            f"{event.duration_seconds:g}s" if event.duration_seconds is not None else "unavailable"
        )
        transcript = self._format_transcript(event.transcript)

        return SlackMessage(
            text=f"Bolna call completed: {execution_id}",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Bolna call completed*"},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*ID:*\n{execution_id}"},
                        {"type": "mrkdwn", "text": f"*Agent ID:*\n{agent_id}"},
                        {"type": "mrkdwn", "text": f"*Duration:*\n{duration}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Transcript:*\n{transcript}"},
                },
            ],
        )

    def post_alert(self, event: BolnaEvent) -> SlackPostResult:
        payload = self.build_message(event).model_dump()
        payload["channel"] = self.default_channel
        response = self._request("chat.postMessage", payload)
        return SlackPostResult(channel=response["channel"], ts=response["ts"])

    def update_alert(self, event: BolnaEvent, channel: str, ts: str) -> None:
        payload = self.build_message(event).model_dump()
        payload["channel"] = channel
        payload["ts"] = ts
        self._request("chat.update", payload)

    def _request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.bot_token:
            raise SlackApiError("SLACK_BOT_TOKEN is not configured")
        if not self.default_channel:
            raise SlackApiError("SLACK_CHANNEL_ID is not configured")

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"https://slack.com/api/{method}",
                    headers={
                        "Authorization": f"Bearer {self.bot_token}",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    json=payload,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SlackApiError(f"Slack API request failed: {exc}") from exc

        body = response.json()
        if not body.get("ok"):
            raise SlackApiError(body.get("error", "Unknown Slack API error"))
        return body

    def _format_transcript(self, transcript: str | None) -> str:
        if not transcript:
            return "Transcript unavailable"
        if len(transcript) <= self.transcript_max_chars:
            return transcript
        truncated = transcript[: self.transcript_max_chars].rstrip()
        return f"{truncated}...(truncated)"
