from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass

from fastapi import FastAPI, Header, HTTPException, status

from app.bolna import BolnaClient
from app.config import Settings, get_settings
from app.models import BolnaEvent
from app.registry import AlertRegistry
from app.service import OrchestrationService
from app.slack import SlackPublisher


@dataclass
class AppContainer:
    settings: Settings
    registry: AlertRegistry
    service: OrchestrationService


def build_container(settings: Settings) -> AppContainer:
    registry = AlertRegistry(settings.sqlite_path)
    slack_publisher = SlackPublisher(
        bot_token=settings.slack_bot_token,
        default_channel=settings.slack_channel_id,
        transcript_max_chars=settings.transcript_max_chars,
    )
    bolna_client = BolnaClient(
        api_key=settings.bolna_api_key,
        base_url=settings.bolna_api_base_url,
    )
    service = OrchestrationService(
        registry=registry,
        slack_publisher=slack_publisher,
        bolna_client=bolna_client,
        slack_max_retries=settings.slack_max_retries,
        slack_retry_backoff_seconds=settings.slack_retry_backoff_seconds,
    )
    return AppContainer(settings=settings, registry=registry, service=service)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    container = build_container(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        container.registry.initialize()
        yield

    app = FastAPI(title="Bolna Slack Alert Integration", lifespan=lifespan)
    app.state.container = container

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhooks/bolna/calls")
    def bolna_webhook(
        payload: BolnaEvent,
        x_bolna_webhook_secret: str | None = Header(default=None),
    ) -> dict[str, object]:
        if x_bolna_webhook_secret != app.state.container.settings.bolna_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret",
            )

        try:
            result = app.state.container.service.handle_webhook(payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        if isinstance(result, dict):
            return result
        return asdict(result)

    return app


app = create_app()
