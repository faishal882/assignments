# Repository Guidelines

## Project Structure & Module Organization

The application code lives in `app/`. `app/main.py` exposes the FastAPI app and webhook route. Supporting modules are split by responsibility: `config.py` for environment-backed settings, `registry.py` for SQLite deduplication, `slack.py` for Slack message delivery, `bolna.py` for Bolna API access, and `service.py` for end-to-end orchestration.

Tests live in `tests/` and mirror the runtime behavior:
- `test_http.py` for webhook endpoint behavior
- `test_registry.py` for SQLite alert registry behavior
- `test_service.py` for orchestration, retries, and transcript recovery

Project docs live at the repo root: `README.md`, `CONTEXT.md`, `PRD.md`, and `plans/`.

## Build, Test, and Development Commands

- `uv sync --dev`
Installs runtime and test dependencies into the local environment.

- `uv run uvicorn app.main:app --reload`
Runs the FastAPI service locally with auto-reload.

- `uv run pytest`
Runs the full test suite.

- `uv run pytest tests/test_service.py`
Runs a focused test file while iterating on orchestration logic.

## Coding Style & Naming Conventions

Use Python 3.12 with 4-space indentation and standard type hints throughout. Keep modules narrowly scoped and prefer explicit names such as `AlertRegistry`, `SlackPublisher`, and `OrchestrationService`.

Use:
- `snake_case` for files, functions, variables
- `PascalCase` for classes
- short, behavior-oriented docstrings only when needed

Avoid mixing HTTP, persistence, and third-party API logic in the same function.

## Testing Guidelines

Use `pytest` for all tests. Favor behavior-focused tests over implementation-detail tests. Validate outcomes such as duplicate suppression, retry behavior, Slack payload shaping, and transcript recovery.

Name test files `test_*.py` and test functions `test_<expected_behavior>()`.

## Commit & Pull Request Guidelines

Recent history uses short, imperative, one-line commit messages, for example:
- `Add FastAPI project scaffold`
- `Implement Bolna Slack webhook service`
- `Add integration service tests`

Keep commits small and logically grouped. For pull requests, include:
- a short summary of behavior added or changed
- setup or config changes
- test evidence (`uv run pytest`)
- sample webhook or Slack output when behavior changes are user-visible

## Security & Configuration Tips

Never commit `.env`, SQLite runtime files, or secrets. Configure `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `BOLNA_WEBHOOK_SECRET`, and optional `BOLNA_API_KEY` through environment variables only.
