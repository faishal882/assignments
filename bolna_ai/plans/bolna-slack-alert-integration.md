# Plan: Bolna Call Completion Slack Alert Integration

> Source PRD: [PRD.md](../PRD.md)

## Architectural decisions

Durable decisions that apply across all phases:

- **Routes**: expose a single inbound webhook route at `POST /webhooks/bolna/calls`.
- **Schema**: persist an alert registry keyed by `execution_id`, with stored alert state sufficient to prevent duplicate posts and support updating an existing Slack message after transcript recovery.
- **Key models**: `Call Completed Event`, `Execution ID`, `Deliverable Alert`, `Transcript Recovery`, `Alert Message`, `Alert Registry`.
- **Authentication**: accept inbound webhooks only when a shared secret under our control is present and valid.
- **Third-party boundaries**: Bolna provides the completed-call webhook and optional recovery fetch; Slack receives the outbound alert and any later message update.
- **Reliability model**: treat Bolna `status=completed` as the canonical trigger, model inbound delivery as at-least-once, deduplicate by `execution_id`, and record success only after Slack accepts the alert.
- **Runtime shape**: implement as a standalone FastAPI service with synchronous SQLite access, configured through environment variables, and demoed locally through a public tunnel.

---

## Phase 1: Completed Call Alert Skeleton

**User stories**: 1, 2, 3, 4, 12, 13, 19, 20, 22, 23

### What to build

Create the thinnest complete path from a Bolna completed-call webhook to a Slack notification. A valid `completed` webhook should be accepted by the service, non-completed events should be ignored, and a Slack message should be posted with the call identifier, agent identifier, and duration using environment-based configuration.

### Acceptance criteria

- [ ] A valid webhook request to `POST /webhooks/bolna/calls` with `status=completed` results in one Slack alert.
- [ ] A webhook with any non-completed status is acknowledged without creating a Slack alert.
- [ ] The alert includes `id`, `agent_id`, and duration, and the service reads required credentials and routing values from environment variables.
- [ ] Requests without the expected shared secret are rejected.

---

## Phase 2: Durable Deduplication

**User stories**: 10, 11, 14, 15, 18, 24, 25

### What to build

Extend the end-to-end path so repeated completed-call webhooks for the same `Execution ID` do not create duplicate Slack alerts. Introduce the durable alert registry and wire it into the webhook flow so that the integration remains correct across retries and process restarts.

### Acceptance criteria

- [ ] The service persists completed alert state keyed by `execution_id`.
- [ ] Re-sending the same completed webhook does not create a second Slack alert.
- [ ] Duplicate suppression still works after restarting the service.
- [ ] A call is only recorded as processed after Slack has accepted the alert.

---

## Phase 3: Readable Transcript Delivery

**User stories**: 5, 6, 7, 8, 24, 25

### What to build

Upgrade the Slack alert into a structured message that includes transcript content when available and remains readable when the transcript is long or absent. The same end-to-end webhook flow should now produce a deliverable alert with a transcript excerpt or an explicit transcript-unavailable state.

### Acceptance criteria

- [ ] Completed webhooks with transcript data produce a structured Slack message that includes a transcript excerpt.
- [ ] Long transcripts are truncated in the alert rather than emitted in full.
- [ ] Completed webhooks without transcript data still produce an alert that explicitly indicates transcript unavailability.
- [ ] The fallback text still summarizes the alert when rich blocks are unavailable.

---

## Phase 4: Transcript Recovery And Message Update

**User stories**: 9, 16, 24, 25

### What to build

Add the bounded recovery path for missing transcript data. When the initial completed webhook lacks transcript content, the service should make one Bolna recovery fetch and, if transcript data becomes available, update the original Slack message so the channel still contains one final alert for the call.

### Acceptance criteria

- [ ] When a completed webhook arrives without transcript data, the service performs one recovery fetch to Bolna.
- [ ] If recovery returns transcript data, the existing Slack alert is updated instead of creating a second message.
- [ ] If recovery still does not return transcript data, no further polling occurs.
- [ ] The alert registry retains enough Slack message state to support a later update.

---

## Phase 5: Resilient Posting Flow

**User stories**: 17, 18, 21, 24, 25

### What to build

Harden the complete integration flow so transient Slack failures are retried in a bounded way and the service is straightforward to demonstrate in a local tunnel-based environment. This slice should make the end-to-end workflow reliable enough for assignment review without expanding into production infrastructure.

### Acceptance criteria

- [ ] Slack post and update attempts use a bounded retry strategy for transient failures.
- [ ] Failed Slack attempts do not prematurely mark an `Execution ID` as processed.
- [ ] The service behavior is documented clearly enough to run locally and expose through a public tunnel for Bolna webhook delivery.
- [ ] Tests cover retry behavior and success-only persistence at the workflow boundary.
