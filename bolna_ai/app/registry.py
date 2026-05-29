from __future__ import annotations

import sqlite3
from contextlib import closing
from enum import StrEnum

from app.models import AlertRecord


class ClaimResult(StrEnum):
    CLAIMED = "claimed"
    POSTED = "posted"
    PROCESSING = "processing"


class AlertRegistry:
    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path

    def initialize(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    execution_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    slack_channel TEXT,
                    slack_ts TEXT,
                    transcript_recovered INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def claim(self, execution_id: str, stale_after_seconds: int) -> ClaimResult:
        with sqlite3.connect(self.sqlite_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO alerts (execution_id, state)
                    VALUES (?, 'processing')
                    """,
                    (execution_id,),
                )
                conn.commit()
                return ClaimResult.CLAIMED
            except sqlite3.IntegrityError:
                pass

            conn.row_factory = sqlite3.Row
            with closing(
                conn.execute(
                    """
                    SELECT state
                    FROM alerts
                    WHERE execution_id = ?
                    """,
                    (execution_id,),
                )
            ) as cursor:
                row = cursor.fetchone()

            if row is None:
                return ClaimResult.PROCESSING
            if row["state"] == "posted":
                return ClaimResult.POSTED

            stale_window = f"-{max(1, stale_after_seconds)} seconds"
            cursor = conn.execute(
                """
                UPDATE alerts
                SET updated_at = CURRENT_TIMESTAMP
                WHERE execution_id = ?
                  AND state = 'processing'
                  AND updated_at <= datetime('now', ?)
                """,
                (execution_id, stale_window),
            )
            conn.commit()
            if cursor.rowcount == 1:
                return ClaimResult.CLAIMED
            return ClaimResult.PROCESSING

    def get(self, execution_id: str) -> AlertRecord | None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            with closing(
                conn.execute(
                    """
                    SELECT execution_id, state, slack_channel, slack_ts, transcript_recovered
                    FROM alerts
                    WHERE execution_id = ?
                    """,
                    (execution_id,),
                )
            ) as cursor:
                row = cursor.fetchone()

        if row is None:
            return None

        return AlertRecord(
            execution_id=row["execution_id"],
            state=row["state"],
            slack_channel=row["slack_channel"],
            slack_ts=row["slack_ts"],
            transcript_recovered=bool(row["transcript_recovered"]),
        )

    def mark_posted(self, execution_id: str, slack_channel: str, slack_ts: str) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                UPDATE alerts
                SET state = 'posted',
                    slack_channel = ?,
                    slack_ts = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE execution_id = ?
                """,
                (slack_channel, slack_ts, execution_id),
            )
            conn.commit()

    def mark_transcript_recovered(self, execution_id: str) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                UPDATE alerts
                SET transcript_recovered = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE execution_id = ?
                """,
                (execution_id,),
            )
            conn.commit()

    def release_claim(self, execution_id: str) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                DELETE FROM alerts
                WHERE execution_id = ? AND state = 'processing'
                """,
                (execution_id,),
            )
            conn.commit()
