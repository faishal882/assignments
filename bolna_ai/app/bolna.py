from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.models import BolnaEvent


@dataclass
class BolnaClient:
    api_key: str
    base_url: str
    timeout_seconds: float = 10.0

    def fetch_execution(self, execution_id: str) -> BolnaEvent | None:
        if not self.api_key:
            return None

        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get(
                f"/executions/{execution_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

        response.raise_for_status()
        return BolnaEvent.model_validate(response.json())
