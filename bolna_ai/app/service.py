from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from app.bolna import BolnaApiError
from app.models import BolnaEvent
from app.registry import AlertRegistry
from app.slack import SlackApiError, SlackPublisher


class BolnaExecutionFetcher(Protocol):
    def fetch_execution(self, execution_id: str) -> BolnaEvent | None: ...


@dataclass
class ProcessingResult:
    status: str
    execution_id: str | None = None
    transcript_recovered: bool = False


@dataclass
class OrchestrationService:
    registry: AlertRegistry
    slack_publisher: SlackPublisher
    bolna_client: BolnaExecutionFetcher
    slack_max_retries: int
    slack_retry_backoff_seconds: float

    def handle_webhook(self, event: BolnaEvent) -> ProcessingResult:
        if event.status != "completed":
            return ProcessingResult(status="ignored", execution_id=event.canonical_execution_id)

        execution_id = event.canonical_execution_id
        if not execution_id:
            raise ValueError("Webhook payload missing execution identifier")

        existing = self.registry.get(execution_id)
        if existing and existing.state == "posted":
            return ProcessingResult(status="duplicate", execution_id=execution_id)

        if not existing and not self.registry.claim(execution_id):
            return ProcessingResult(status="duplicate", execution_id=execution_id)

        try:
            post_result = self._retry_slack_post(event)
            self.registry.mark_posted(execution_id, post_result.channel, post_result.ts)

            transcript_recovered = self._maybe_recover_transcript(
                event, post_result.channel, post_result.ts
            )
            return ProcessingResult(
                status="processed",
                execution_id=execution_id,
                transcript_recovered=transcript_recovered,
            )
        except Exception:
            self.registry.release_claim(execution_id)
            raise

    def _retry_slack_post(self, event: BolnaEvent):
        return self._retry(lambda: self.slack_publisher.post_alert(event))

    def _maybe_recover_transcript(self, event: BolnaEvent, channel: str, ts: str) -> bool:
        if event.transcript:
            return False

        execution_id = event.canonical_execution_id
        if not execution_id:
            return False

        try:
            recovered_event = self.bolna_client.fetch_execution(execution_id)
        except BolnaApiError:
            return False

        if not recovered_event or not recovered_event.transcript:
            return False

        merged_event = event.with_transcript(recovered_event.transcript)
        try:
            self._retry(lambda: self.slack_publisher.update_alert(merged_event, channel, ts))
        except SlackApiError:
            return False

        self.registry.mark_transcript_recovered(execution_id)
        return True

    def _retry(self, operation):
        attempts = max(1, self.slack_max_retries)
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except Exception as exc:  # pragma: no cover - exercised via behavior tests
                last_error = exc
                if attempt == attempts:
                    break
                time.sleep(self.slack_retry_backoff_seconds * attempt)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Retry operation failed without an exception")
