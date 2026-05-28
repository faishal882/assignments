# Bolna Slack Alert Integration

This context describes the domain language for a small integration that notifies Slack when a Bolna voice call completes.

## Language

**Call Completed Event**:
The canonical signal that a Bolna call has ended successfully enough for downstream processing. In this integration, it is the Bolna webhook update whose status is `completed`.
_Avoid_: ended call, finished call, final callback

**Alert Delivery**:
The reliability contract for emitting a Slack notification after a Call Completed Event. In this integration, delivery is at-least-once into the integration service, with deduplication before posting to Slack.
_Avoid_: fire-and-forget, exactly-once

**Execution ID**:
The stable identity of a single Bolna call execution. In this integration, it is the idempotency key for ensuring one Slack alert per completed call.
_Avoid_: alert ID, message ID, retry ID

**Deliverable Alert**:
An alert that must be emitted once a Call Completed Event is received, even if some requested fields are missing. In this integration, a missing transcript degrades the alert content but does not block delivery.
_Avoid_: fully hydrated alert, complete payload only

**Transcript Recovery**:
The bounded fallback used when a Deliverable Alert is emitted without transcript data. In this integration, the service may perform a single follow-up fetch from Bolna to enrich the alert, but it does not poll indefinitely.
_Avoid_: primary transcript source, background polling loop

**Webhook Trust**:
The rule for deciding whether an incoming webhook should be accepted for processing. In this integration, the simplest acceptable model is a shared secret under our control, without IP allowlisting.
_Avoid_: full network perimeter validation, unsigned public webhook

**Alert Registry**:
The durable record of which completed calls have already produced a Slack alert. In this integration, it is a SQLite-backed store keyed by Execution ID.
_Avoid_: in-memory cache, ephemeral dedupe map

**Alert Message**:
The Slack representation of a completed call notification. In this integration, it is a structured Slack message with blocks and a fallback text summary.
_Avoid_: raw transcript dump, plain text only

**Transcript Excerpt**:
The portion of a call transcript included in the Alert Message. In this integration, long transcripts are truncated for readability rather than split across multiple Slack messages.
_Avoid_: full transcript in alert, threaded transcript chunks

**Posting Retry**:
The bounded retry policy used when Slack does not accept an Alert Message on the first attempt. In this integration, a call is only recorded in the Alert Registry after Slack accepts the message.
_Avoid_: mark-before-send, infinite retry loop

**Integration Service**:
The runtime boundary that owns webhook intake, deduplication, transcript recovery, and Slack notification delivery. In this integration, it is a single standalone service.
_Avoid_: distributed workflow, embedded side feature

**Implementation Stack**:
The application framework and core libraries used to realize the Integration Service. In this integration, the preferred stack is Python with FastAPI and SQLite.
_Avoid_: Node service, multi-framework runtime

**Alert Registry Access**:
The way the Integration Service reads and writes deduplication state. In this integration, SQLite access is synchronous and in-process.
_Avoid_: async ORM layer, external database dependency

**Execution Environment**:
The assumed runtime environment for demonstrating the Integration Service. In this integration, the default environment is a local FastAPI process exposed through a public tunnel.
_Avoid_: production deployment requirement, platform-specific hosting

**Alert Update**:
The mutation of an existing Alert Message after Transcript Recovery succeeds. In this integration, recovered transcript data updates the original Slack alert instead of creating a second notification.
_Avoid_: duplicate alert, follow-up transcript message

**Runtime Configuration**:
The externally supplied values needed to run the Integration Service in a given environment. In this integration, credentials, channel selection, webhook secret, and SQLite path are provided through environment variables.
_Avoid_: hardcoded secrets, code-level environment binding
