# Emergent production-debugging interview guide

## What this round is actually testing

The candidate account describes a roughly one-hour BarRaiser technical discussion built around realistic customer and production incidents. The interviewer is evaluating whether you can create order from incomplete information—not whether you recognize every error immediately.

Your score is likely driven by five signals:

1. You clarify impact and scope before diagnosing.
2. You form several plausible hypotheses and rank them using evidence.
3. You choose diagnostic steps that can prove or disprove a hypothesis.
4. You mitigate safely, verify recovery, and prevent recurrence.
5. You keep the customer informed in plain language without inventing certainty.

## Use the C-L-E-A-R response structure

### C — Clarify

Start with impact, scope, timeline, and change history.

Say: “Before proposing a cause, I want to establish who is affected, when this started, whether it is reproducible, and what changed near that time.”

Ask:

- Is this one user, one tenant, one region, or everyone?
- What does “not working” mean—error, empty UI, slowness, or wrong data?
- When was the last known successful request?
- Is production uniquely affected? Which browser, device, route, or account?
- What deployed or changed in configuration, dependencies, DNS, certificates, data, or traffic?

### L — Locate

Trace one failed request across layers instead of randomly inspecting tools.

Use this order when applicable:

`Browser → DNS/TLS → CDN/proxy → application → dependency/database`

Request a timestamp, request/correlation ID, sanitized error, HTTP method/status, relevant headers, and logs from the same attempt. Compare a failed case with a successful one.

### E — Explain hypotheses

Give a short ranked list. Attach evidence to each item.

Say: “My leading hypothesis is X because of Y. Z is also possible, but less likely because of A. I would run B next; if it returns C, that supports X, while D would eliminate it.”

Do not list ten unranked causes. Three is usually enough:

- Most likely based on current evidence.
- Most dangerous if true.
- A plausible alternative that is cheap to eliminate.

### A — Act safely

Separate mitigation from root-cause correction.

- Mitigation: rollback, disable a feature, route around failure, scale, throttle, or provide a safe workaround.
- Fix: make the smallest justified change and use canary/staged rollout where possible.
- Verification: repeat the exact failed journey and inspect technical plus customer-facing success signals.
- Prevention: tests, validation, alerting, runbooks, limits, or safer deployment controls.

Never restart, delete, rotate, or change production blindly. State the risk and rollback path.

### R — Reassure with facts

A useful customer update has four parts:

1. Acknowledge impact: “I understand checkout is blocking your launch.”
2. State verified facts: “We can reproduce it and have isolated the failure to…”
3. State current action: “We are rolling back the affected revision…”
4. Promise the next update by a concrete time, even if there is no resolution yet.

Avoid blame, raw jargon, guesses presented as facts, and promises you cannot control.

## High-yield fundamentals to revise

### Browser and frontend

- Console errors and source maps; Network request timing, headers, payload, response, and initiator.
- HTTP cache versus service workers; cookies and storage; same-origin policy and CORS preflight.
- Render/runtime errors, failed assets, stale bundles, environment variables embedded at build time.

### HTTP, APIs, and authentication

- `400` malformed request, `401` missing/invalid identity, `403` authenticated but unauthorized, `404`, `409`, `422`, `429`, and `5xx` failures.
- Trace method, URL, DNS/TLS, proxy, route, middleware, handler, dependency, and response.
- JWT issuer/audience/expiry, cookie domain/path/SameSite/Secure, OAuth redirect URIs, and clock skew.
- Never ask a customer to paste credentials or complete tokens.

### Deployment and infrastructure

- Build success does not imply startup or readiness success.
- Process command, bind address, injected port, health check, environment variables, secrets, resources, and filesystem assumptions.
- DNS record and propagation, certificate hostname/chain/expiry, load balancer/proxy configuration, container logs and platform events.

### Databases

- Connectivity, pool exhaustion, slow queries, locks/deadlocks, transaction boundaries, migrations, permissions, and data consistency.
- Prefer evidence such as query duration, active sessions, wait events, pool metrics, and execution plans.
- Back up and establish blast radius before any destructive repair.

### AI and agents

- Capture the complete trace: prompt/version, model, tool inputs/outputs, state, retries, latency, and token/cost use.
- Separate model variability from deterministic orchestration failures.
- Add hard limits: max steps, timeouts, retry caps, budget caps, repeated-call detection, idempotency, and human escalation.
- Treat model output as untrusted input; validate tool arguments and permissions.

## Questions you should rehearse aloud

1. A site is blank after deployment, but its API returns `200`. What do you inspect first?
2. Login succeeds but every subsequent request returns `401` only in production.
3. An API works in curl but the browser blocks it. Explain why and debug the preflight.
4. A container builds but repeatedly fails readiness checks.
5. A custom domain works for some users but shows certificate errors for others.
6. Checkout latency spikes without high CPU or a recent deployment.
7. A migration succeeded, but the new application revision says a column is missing.
8. An AI agent repeats the same tool call and consumes the customer’s budget.
9. A customer says, “Your platform deleted my data.” What do you say and investigate?
10. Your rollback did not restore service. How does your incident approach change?

## A strong 90-second answer template

“First I’d confirm the impact: who is affected, the exact failure, when it began, and any nearby change. I’d ask for one failed request with its timestamp and correlation ID so I can follow it across the browser, edge, application, and dependency logs.

Based on the current evidence, my leading hypotheses are [X] and [Y]. I rank X first because [evidence]. I would check [specific signal] next. A result of [A] supports X; [B] would eliminate it and move Y up.

While investigating, I’d reduce customer impact with [safe mitigation], with [rollback path]. Once fixed, I’d repeat the original journey and monitor [success metric], [error metric], and [dependency metric]. I’d tell the customer what we have verified, what we are doing now, and when they will hear from us next.”

## During the BarRaiser call

- Think aloud, but keep a visible hierarchy: facts → hypotheses → test → decision.
- Ask for evidence; do not assume an unseen log says what you need.
- If the interviewer supplies new evidence, explicitly update your ranking.
- Say when you would escalate and what context you would hand off.
- Close every scenario with mitigation, verification, prevention, and a customer update.

Source used to shape this guide: [Roshni Kumari’s candidate account](https://medium.com/@roshni_k06/first-interview-experience-with-emergent-8458adcf2e91).
