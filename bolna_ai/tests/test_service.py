from dataclasses import dataclass, field

import pytest

from app.models import BolnaEvent, SlackPostResult
from app.registry import AlertRegistry
from app.service import OrchestrationService
from app.slack import SlackApiError, SlackPublisher


@dataclass
class FakeSlackPublisher:
    post_calls: list[BolnaEvent] = field(default_factory=list)
    update_calls: list[tuple[BolnaEvent, str, str]] = field(default_factory=list)
    fail_posts_remaining: int = 0

    def post_alert(self, event: BolnaEvent) -> SlackPostResult:
        if self.fail_posts_remaining > 0:
            self.fail_posts_remaining -= 1
            raise SlackApiError("temporary_error")
        self.post_calls.append(event)
        return SlackPostResult(channel="C123", ts="111.222")

    def update_alert(self, event: BolnaEvent, channel: str, ts: str) -> None:
        self.update_calls.append((event, channel, ts))


@dataclass
class FakeBolnaClient:
    recovered_event: BolnaEvent | None = None
    fetch_calls: list[str] = field(default_factory=list)

    def fetch_execution(self, execution_id: str) -> BolnaEvent | None:
        self.fetch_calls.append(execution_id)
        return self.recovered_event


def make_service(tmp_path, slack_publisher, bolna_client):
    registry = AlertRegistry(str(tmp_path / "alerts.db"))
    registry.initialize()
    return OrchestrationService(
        registry=registry,
        slack_publisher=slack_publisher,
        bolna_client=bolna_client,
        slack_max_retries=2,
        slack_retry_backoff_seconds=0,
    )


def test_completed_webhook_posts_once_and_dedupes(tmp_path):
    slack = FakeSlackPublisher()
    bolna = FakeBolnaClient()
    service = make_service(tmp_path, slack, bolna)
    event = BolnaEvent(id="exec-1", agent_id="agent-1", status="completed", conversation_time=42)

    first = service.handle_webhook(event)
    second = service.handle_webhook(event)

    assert first.status == "processed"
    assert second.status == "duplicate"
    assert len(slack.post_calls) == 1


def test_missing_transcript_triggers_one_recovery_and_update(tmp_path):
    slack = FakeSlackPublisher()
    bolna = FakeBolnaClient(
        recovered_event=BolnaEvent(
            id="exec-1",
            agent_id="agent-1",
            status="completed",
            transcript="Recovered transcript",
        )
    )
    service = make_service(tmp_path, slack, bolna)
    event = BolnaEvent(id="exec-1", agent_id="agent-1", status="completed")

    result = service.handle_webhook(event)

    assert result.transcript_recovered is True
    assert bolna.fetch_calls == ["exec-1"]
    assert len(slack.update_calls) == 1
    updated_event, channel, ts = slack.update_calls[0]
    assert updated_event.transcript == "Recovered transcript"
    assert channel == "C123"
    assert ts == "111.222"


def test_failed_slack_post_does_not_leave_processed_record(tmp_path):
    slack = FakeSlackPublisher(fail_posts_remaining=2)
    bolna = FakeBolnaClient()
    service = make_service(tmp_path, slack, bolna)
    event = BolnaEvent(id="exec-1", agent_id="agent-1", status="completed")

    with pytest.raises(SlackApiError):
        service.handle_webhook(event)

    assert service.registry.get("exec-1") is None


def test_build_message_truncates_long_transcript():
    publisher = SlackPublisher(
        bot_token="token",
        default_channel="C123",
        transcript_max_chars=10,
    )
    event = BolnaEvent(
        id="exec-1",
        agent_id="agent-1",
        status="completed",
        transcript="abcdefghijklmnopqrstuvwxyz",
        conversation_time=12,
    )

    message = publisher.build_message(event)

    assert message.text == "Bolna call completed: exec-1"
    assert "abcdefghij...(truncated)" in message.blocks[2]["text"]["text"]
