# PRD: Bolna Call Completion Slack Alert Integration

## Problem Statement

The user needs a simple integration that notifies a Slack channel whenever a Bolna call ends. The notification must include the call identifier, agent identifier, duration, and transcript. The solution should be appropriate for a test project: easy to run locally, easy to demonstrate, and reliable enough to avoid obvious duplicate alerts or missing notifications during normal retries.

## Solution

Build a standalone FastAPI service that receives Bolna webhook updates, treats the `completed` webhook as the canonical call-completed signal, and posts a structured Slack alert for each completed call. The service will deduplicate alerts by Bolna execution ID using SQLite, send the alert even when transcript data is initially missing, and perform one bounded Bolna fetch to recover transcript data and update the original Slack message if recovery succeeds.

## User Stories

1. As a recruiter or operator, I want a Slack alert when a Bolna call completes, so that I know the call finished without logging into Bolna.
2. As a recruiter or operator, I want the alert to include the call ID, so that I can trace the alert back to the specific Bolna execution.
3. As a recruiter or operator, I want the alert to include the agent ID, so that I know which Bolna agent handled the call.
4. As a recruiter or operator, I want the alert to include the call duration, so that I can quickly assess how long the interaction lasted.
5. As a recruiter or operator, I want the alert to include the transcript, so that I can review the conversation content from Slack.
6. As a recruiter or operator, I want the transcript to be readable in Slack, so that the message remains useful without opening another system.
7. As a recruiter or operator, I want long transcripts shortened in the main alert, so that the channel remains readable.
8. As a recruiter or operator, I want the alert to be sent even if transcript data is temporarily missing, so that call completion is never hidden behind a transcript-generation delay.
9. As a recruiter or operator, I want the original Slack message updated if transcript recovery succeeds later, so that I still end up with a complete final alert.
10. As a recruiter or operator, I want exactly one visible Slack alert per completed call, so that retries do not create channel noise.
11. As a developer, I want Bolna webhook retries to be safe, so that duplicate inbound events do not create duplicate outbound alerts.
12. As a developer, I want the integration to use the Bolna completed webhook as the canonical completion signal, so that the workflow has one clear source of truth.
13. As a developer, I want the service to ignore non-completed webhook events, so that Slack only receives end-of-call notifications.
14. As a developer, I want a durable deduplication store, so that restarting the service does not re-alert already processed calls.
15. As a developer, I want the deduplication key to be the Bolna execution ID, so that retries collapse onto the same completed call identity.
16. As a developer, I want the service to recover missing transcript data with one bounded follow-up fetch, so that the implementation stays simple and does not become a polling system.
17. As a developer, I want the Slack posting workflow to retry bounded transient failures, so that temporary Slack errors do not immediately lose alerts.
18. As a developer, I want a call to be marked processed only after Slack accepts the message, so that failed posts can still be retried safely.
19. As a developer, I want the service to expose a single webhook endpoint, so that local setup and demonstration remain simple.
20. As a developer, I want the service to run locally with FastAPI and SQLite, so that the assignment does not depend on external infrastructure beyond Bolna and Slack.
21. As a developer, I want to expose the local service through a public tunnel, so that Bolna can reach it during testing.
22. As a developer, I want secrets and environment-specific settings supplied via environment variables, so that credentials are not hardcoded into source code.
23. As a developer, I want a simple shared-secret check on the webhook, so that the assignment avoids an entirely unauthenticated public endpoint.
24. As a reviewer, I want the implementation to be decomposed into small modules with clear responsibilities, so that the code is easy to inspect and test.
25. As a reviewer, I want the most failure-prone logic covered by tests, so that duplicate suppression, retry behavior, and Slack payload generation are verifiable.

## Implementation Decisions

- Build a single standalone integration service rather than embedding the feature into another application.
- Use Python with FastAPI for the HTTP service layer.
- Use SQLite as the durable alert registry.
- Use synchronous, in-process SQLite access rather than an async ORM or external database.
- Treat the Bolna webhook event with `status = completed` as the canonical call-completed event.
- Ignore non-completed webhook events for Slack notification purposes.
- Use Bolna execution ID as the idempotency key for deduplicating alerts.
- Model delivery as at-least-once into the integration service, with deduplication before Slack posting.
- Verify inbound webhooks with a shared secret suitable for a test-project trust model.
- Post a Slack alert even if transcript data is missing from the completed webhook.
- Perform one bounded transcript-recovery fetch from Bolna when transcript data is absent at completion time.
- Update the original Slack message if transcript recovery succeeds after the initial alert.
- Use Slack Block Kit plus fallback text for the alert message shape.
- Truncate long transcript content into a transcript excerpt rather than splitting transcripts into multiple messages or threads.
- Apply bounded retries when Slack post or update attempts fail transiently.
- Persist a completed call as processed only after Slack accepts the initial alert message.
- Store enough alert metadata to support deduplication and message updates after transcript recovery.
- Keep all operational values externalized through environment configuration, including Slack credentials, Slack channel selection, Bolna credentials, webhook secret, and SQLite path.
- Assume a local execution model exposed by a tunnel for demonstration and testing.
- Separate the service into five modules:
- Webhook Intake for request validation, normalization, and filtering.
- Alert Registry for durable deduplication and alert state.
- Transcript Recovery for the single Bolna enrichment fetch.
- Slack Alert Publisher for message construction, posting, and update behavior.
- Orchestration Service for the end-to-end workflow and retry coordination.

## Testing Decisions

- Good tests should validate external behavior and contract boundaries rather than internal implementation details.
- Tests should assert outcomes such as whether duplicates are suppressed, whether a completed event without transcript still produces an alert, whether long transcripts are truncated, whether successful recovery updates the original message, and whether a failed Slack attempt does not prematurely mark a call as processed.
- The Alert Registry should be tested for durable deduplication semantics and uniqueness behavior around execution IDs.
- The Slack Alert Publisher should be tested for message construction, transcript truncation, fallback text behavior, and update semantics.
- The Orchestration Service should be tested for the full workflow: intake of a completed event, dedupe checks, posting retries, transcript recovery decisions, and final success persistence.
- The Webhook Intake layer can be covered with HTTP-level integration tests to confirm secret verification and non-completed event filtering.
- Transcript Recovery should be tested with mocked Bolna responses, including absent transcript, successful enrichment, and failed recovery.
- Since the repo currently has no prior art, the tests should establish clean patterns around behavior-focused unit tests and a small number of HTTP integration tests.

## Out of Scope

- Production-grade infrastructure, hosting, containerization, or CI/CD setup.
- IP allowlisting or advanced webhook signature verification.
- Infinite polling or long-running background transcript synchronization.
- Multi-channel Slack routing, per-agent routing, or user-configurable routing rules.
- Rich Slack interactivity such as buttons, modals, or acknowledgements.
- Storing or presenting full transcripts losslessly inside Slack.
- Admin dashboards, analytics views, or a UI for browsing delivered alerts.
- Generalized event processing for other Bolna statuses beyond completed-call notifications.

## Further Notes

- The repository currently contains only domain glossary documentation and no application code, so this PRD defines the initial implementation shape rather than a modification to an existing service.
- The design intentionally optimizes for a clean assignment submission rather than production-scale hardening.
- There is no Git repository or GitHub remote in this workspace, so this PRD is captured locally instead of being submitted as a GitHub issue.
