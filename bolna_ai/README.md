# Bolna Slack Alert Integration

Standalone FastAPI service that receives Bolna call webhooks and posts a Slack alert when a call reaches `completed`.

## Features

- Accepts Bolna webhook updates at `POST /webhooks/bolna/calls`
- Ignores non-`completed` statuses
- Deduplicates by Bolna execution ID with SQLite
- Posts structured Slack messages with transcript excerpts
- Recovers missing transcript data with one Bolna fetch
- Updates the original Slack message if recovery succeeds

## Configuration

Set these environment variables:

- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID`
- `BOLNA_WEBHOOK_SECRET`
- `BOLNA_API_KEY` (required only for transcript recovery)
- `BOLNA_API_BASE_URL` (default: `https://api.bolna.ai`)
- `SQLITE_PATH` (default: `alerts.db`)
- `SLACK_MAX_RETRIES` (default: `3`)
- `SLACK_RETRY_BACKOFF_SECONDS` (default: `0.5`)
- `TRANSCRIPT_MAX_CHARS` (default: `3000`)

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Expose the local server with a public tunnel such as `ngrok` and configure the Bolna agent webhook URL to:

```text
https://<public-host>/webhooks/bolna/calls
```

Send the shared secret in the `X-Bolna-Webhook-Secret` header.

## Tests

```bash
uv run pytest
```
