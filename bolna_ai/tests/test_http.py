from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.slack import SlackApiError


def make_client(tmp_path):
    settings = Settings(
        slack_bot_token="token",
        slack_channel_id="C123",
        bolna_webhook_secret="secret",
        sqlite_path=str(tmp_path / "alerts.db"),
        slack_max_retries=1,
        slack_retry_backoff_seconds=0,
    )
    app = create_app(settings)

    class StubService:
        def __init__(self):
            self.calls = []

        def handle_webhook(self, payload, request_id=None):
            self.calls.append((payload, request_id))
            return {
                "status": "ignored",
                "execution_id": payload.canonical_execution_id,
                "request_id": request_id,
            }

    stub = StubService()
    app.state.container.service = stub
    return app, stub


def test_webhook_rejects_invalid_secret(tmp_path):
    app, _ = make_client(tmp_path)

    with TestClient(app) as client:
        response = client.post("/webhooks/bolna/calls", json={"id": "exec-1", "status": "completed"})

    assert response.status_code == 401


def test_webhook_accepts_valid_secret_and_forwards_payload(tmp_path):
    app, stub = make_client(tmp_path)

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/bolna/calls",
            headers={"X-Bolna-Webhook-Secret": "secret", "X-Request-Id": "req-123"},
            json={"id": "exec-1", "status": "queued"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert response.json()["request_id"] == "req-123"
    assert len(stub.calls) == 1
    assert stub.calls[0][1] == "req-123"


def test_webhook_maps_slack_failure_to_503(tmp_path):
    app, _ = make_client(tmp_path)

    class FailingService:
        def handle_webhook(self, payload, request_id=None):
            raise SlackApiError("slack unavailable")

    app.state.container.service = FailingService()
    with TestClient(app) as client:
        response = client.post(
            "/webhooks/bolna/calls",
            headers={"X-Bolna-Webhook-Secret": "secret"},
            json={"id": "exec-1", "status": "completed"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "slack unavailable"


def test_get_alert_returns_404_for_missing_execution(tmp_path):
    app, _ = make_client(tmp_path)

    with TestClient(app) as client:
        response = client.get("/alerts/exec-missing")

    assert response.status_code == 404


def test_get_alert_and_list_alerts_return_registry_data(tmp_path):
    app, _ = make_client(tmp_path)

    with TestClient(app) as client:
        registry = client.app.state.container.registry
        registry.claim("exec-1", stale_after_seconds=60)
        registry.mark_posted("exec-1", "C123", "123.456")
        get_response = client.get("/alerts/exec-1")
        list_response = client.get("/alerts")

    assert get_response.status_code == 200
    assert get_response.json()["execution_id"] == "exec-1"
    assert get_response.json()["state"] == "posted"

    assert list_response.status_code == 200
    assert list_response.json()[0]["execution_id"] == "exec-1"
