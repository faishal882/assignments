from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from app.bolna import BolnaApiError
from app.logging_utils import event_context, get_logger
from app.models import BolnaEvent
from app.registry import AlertRegistry, ClaimResult
from app.slack import SlackApiError, SlackPublisher


class BolnaExecutionFetcher(Protocol):
    def fetch_execution(self, execution_id: str) -> BolnaEvent | None: ...


logger = get_logger(__name__)


@dataclass
class ProcessingResult:
    status: str
    execution_id: str | None = None
    transcript_recovered: bool = False
    request_id: str | None = None


@dataclass
class OrchestrationService:
    registry: AlertRegistry
    slack_publisher: SlackPublisher
    bolna_client: BolnaExecutionFetcher
    slack_max_retries: int
    slack_retry_backoff_seconds: float
    processing_claim_timeout_seconds: int

    def handle_webhook(self, event: BolnaEvent, request_id: str | None = None) -> ProcessingResult:
        if event.status != "completed":
            logger.info(
                "Ignoring non-completed Bolna event",
                extra=event_context(
                    request_id=request_id,
                    execution_id=event.canonical_execution_id,
                    status=event.status,
                ),
            )
            return ProcessingResult(
                status="ignored",
                execution_id=event.canonical_execution_id,
                request_id=request_id,
            )

        execution_id = event.canonical_execution_id
        if not execution_id:
            raise ValueError("Webhook payload missing execution identifier")

        claim_result = self.registry.claim(execution_id, self.processing_claim_timeout_seconds)
        if claim_result == ClaimResult.POSTED:
            logger.info(
                "Duplicate completed event ignored after posted alert",
                extra=event_context(request_id=request_id, execution_id=execution_id),
            )
            return ProcessingResult(
                status="duplicate",
                execution_id=execution_id,
                request_id=request_id,
            )
        if claim_result == ClaimResult.PROCESSING:
            logger.info(
                "Duplicate completed event ignored while alert is processing",
                extra=event_context(request_id=request_id, execution_id=execution_id),
            )
            return ProcessingResult(
                status="duplicate",
                execution_id=execution_id,
                request_id=request_id,
            )

        try:
            post_result = self._retry_slack_post(event)
            self.registry.mark_posted(execution_id, post_result.channel, post_result.ts)
            logger.info(
                "Slack alert posted",
                extra=event_context(
                    request_id=request_id,
                    execution_id=execution_id,
                    slack_channel=post_result.channel,
                    slack_ts=post_result.ts,
                ),
            )

            transcript_recovered = self._maybe_recover_transcript(
                event, post_result.channel, post_result.ts, request_id=request_id
            )
            return ProcessingResult(
                status="processed",
                execution_id=execution_id,
                transcript_recovered=transcript_recovered,
                request_id=request_id,
            )
        except Exception:
            self.registry.release_claim(execution_id)
            logger.exception(
                "Webhook processing failed",
                extra=event_context(request_id=request_id, execution_id=execution_id),
            )
            raise

    def _retry_slack_post(self, event: BolnaEvent):
        return self._retry(lambda: self.slack_publisher.post_alert(event))

    def _maybe_recover_transcript(
        self,
        event: BolnaEvent,
        channel: str,
        ts: str,
        request_id: str | None = None,
    ) -> bool:
        if event.transcript:
            return False

        execution_id = event.canonical_execution_id
        if not execution_id:
            return False

        try:
            recovered_event = self.bolna_client.fetch_execution(execution_id)
        except BolnaApiError:
            logger.warning(
                "Transcript recovery fetch failed",
                extra=event_context(request_id=request_id, execution_id=execution_id),
            )
            return False

        if not recovered_event or not recovered_event.transcript:
            logger.info(
                "Transcript recovery returned no transcript",
                extra=event_context(request_id=request_id, execution_id=execution_id),
            )
            return False

        merged_event = event.with_transcript(recovered_event.transcript)
        try:
            self._retry(lambda: self.slack_publisher.update_alert(merged_event, channel, ts))
        except SlackApiError:
            logger.warning(
                "Slack alert update failed after transcript recovery",
                extra=event_context(request_id=request_id, execution_id=execution_id),
            )
            return False

        self.registry.mark_transcript_recovered(execution_id)
        logger.info(
            "Slack alert updated with recovered transcript",
            extra=event_context(
                request_id=request_id,
                execution_id=execution_id,
                slack_channel=channel,
                slack_ts=ts,
            ),
        )
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
