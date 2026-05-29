from app.registry import AlertRegistry


def test_registry_claim_and_mark_posted(tmp_path):
    registry = AlertRegistry(str(tmp_path / "alerts.db"))
    registry.initialize()

    assert registry.claim("exec-1") is True
    assert registry.claim("exec-1") is False

    registry.mark_posted("exec-1", "C123", "123.456")
    record = registry.get("exec-1")

    assert record is not None
    assert record.state == "posted"
    assert record.slack_channel == "C123"
    assert record.slack_ts == "123.456"
