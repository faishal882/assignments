from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.models import BolnaEvent


class BolnaApiError(RuntimeError):
    pass


@dataclass
class BolnaClient:
    api_key: str
    base_url: str
    timeout_seconds: float = 10.0

    def fetch_execution(self, execution_id: str) -> BolnaEvent | None:
        if not self.api_key:
            return None

        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
                response = client.get(
                    f"/executions/{execution_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BolnaApiError(f"Bolna execution fetch failed: {exc}") from exc

        return BolnaEvent.model_validate(response.json())
