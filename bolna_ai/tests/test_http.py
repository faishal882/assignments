from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


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

        def handle_webhook(self, payload):
            self.calls.append(payload)
            return {"status": "ignored", "execution_id": payload.canonical_execution_id}

    stub = StubService()
    app.state.container.service = stub
    return TestClient(app), stub


def test_webhook_rejects_invalid_secret(tmp_path):
    client, _ = make_client(tmp_path)

    response = client.post("/webhooks/bolna/calls", json={"id": "exec-1", "status": "completed"})

    assert response.status_code == 401


def test_webhook_accepts_valid_secret_and_forwards_payload(tmp_path):
    client, stub = make_client(tmp_path)

    response = client.post(
        "/webhooks/bolna/calls",
        headers={"X-Bolna-Webhook-Secret": "secret"},
        json={"id": "exec-1", "status": "queued"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert len(stub.calls) == 1
