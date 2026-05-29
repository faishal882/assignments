from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
import uuid

from fastapi import FastAPI, Header, HTTPException, status

from app.bolna import BolnaApiError
from app.bolna import BolnaClient
from app.config import Settings, get_settings
from app.logging_utils import configure_logging, event_context, get_logger
from app.models import BolnaEvent, WebhookResponse
from app.registry import AlertRegistry
from app.service import OrchestrationService
from app.slack import SlackApiError, SlackPublisher


@dataclass
class AppContainer:
    settings: Settings
    registry: AlertRegistry
    service: OrchestrationService


logger = get_logger(__name__)


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
        processing_claim_timeout_seconds=settings.processing_claim_timeout_seconds,
    )
    return AppContainer(settings=settings, registry=registry, service=service)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    container = build_container(resolved_settings)
    configure_logging()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        container.registry.initialize()
        yield

    app = FastAPI(title="Bolna Slack Alert Integration", lifespan=lifespan)
    app.state.container = container

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/alerts/{execution_id}")
    def get_alert(execution_id: str) -> dict[str, object]:
        record = app.state.container.registry.get(execution_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        return record.model_dump()

    @app.get("/alerts")
    def list_alerts(limit: int = 20) -> list[dict[str, object]]:
        safe_limit = min(max(limit, 1), 100)
        return [record.model_dump() for record in app.state.container.registry.list_recent(safe_limit)]

    @app.post("/webhooks/bolna/calls")
    def bolna_webhook(
        payload: BolnaEvent,
        x_bolna_webhook_secret: str | None = Header(default=None),
        x_request_id: str | None = Header(default=None),
    ) -> dict[str, object]:
        request_id = x_request_id or str(uuid.uuid4())
        if x_bolna_webhook_secret != app.state.container.settings.bolna_webhook_secret:
            logger.warning(
                "Rejected webhook with invalid secret",
                extra=event_context(
                    request_id=request_id,
                    execution_id=payload.canonical_execution_id,
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret",
            )

        try:
            result = app.state.container.service.handle_webhook(payload, request_id=request_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except SlackApiError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except BolnaApiError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        if isinstance(result, dict):
            return result
        return WebhookResponse(**asdict(result)).model_dump()

    return app


app = create_app()
