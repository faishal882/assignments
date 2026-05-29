import sqlite3

from app.registry import AlertRegistry, ClaimResult


def test_registry_claim_and_mark_posted(tmp_path):
    registry = AlertRegistry(str(tmp_path / "alerts.db"))
    registry.initialize()

    assert registry.claim("exec-1", stale_after_seconds=60) == ClaimResult.CLAIMED
    assert registry.claim("exec-1", stale_after_seconds=60) == ClaimResult.PROCESSING

    registry.mark_posted("exec-1", "C123", "123.456")
    record = registry.get("exec-1")

    assert record is not None
    assert record.state == "posted"
    assert record.slack_channel == "C123"
    assert record.slack_ts == "123.456"


def test_registry_reclaims_stale_processing_record(tmp_path):
    db_path = tmp_path / "alerts.db"
    registry = AlertRegistry(str(db_path))
    registry.initialize()
    assert registry.claim("exec-1", stale_after_seconds=60) == ClaimResult.CLAIMED

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE alerts
            SET updated_at = datetime('now', '-120 seconds')
            WHERE execution_id = 'exec-1'
            """
        )
        conn.commit()

    assert registry.claim("exec-1", stale_after_seconds=60) == ClaimResult.CLAIMED
