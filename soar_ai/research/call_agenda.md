# 15-minute call agenda with Henry

Use this if Henry agrees to a short call. The structure keeps the conversation founder-centered and prevents over-presenting.

## 0:00-1:00 — Opener

“I studied Soar from public product/legal/client-route signals. My hypothesis is that the hard problem is not generic flight search; it is making booking feel instant while managing booking state, payment/verification ambiguity, support tooling, and deal-link conversion.”

## 1:00-4:00 — Ask where it hurts

Ask one primary bottleneck question:

“Where is the biggest current bottleneck: shared-link conversion, hold-to-ticket reliability, payment/verification ambiguity, or post-booking support?”

Then shut up and listen.

## 4:00-7:00 — Reflect back the problem

Summarize his answer in operational terms:

- user-facing symptom;
- internal/debugging symptom;
- metric affected;
- why it matters this week.

## 7:00-10:00 — Offer one concrete ownership slice

Pick the matching slice:

- Growth bottleneck → event schema + deal-link funnel dashboard.
- Booking ambiguity → booking state machine + idempotency/retry memo.
- Support bottleneck → fake-data booking timeline/admin console.
- Trust/fraud bottleneck → risk flags + operator handoff workflow.

## 10:00-12:00 — Prove fit briefly

Use only the relevant proof:

- Tailorec for external workflow/state/analytics/product ops.
- AWS/runbooks for production ownership.
- OS project only if low-level debugging comes up.

## 12:00-14:00 — Propose the 48-hour artifact

“I can do this without private access first: fake data, public-signal assumptions, and a short implementation memo listing what I’d need to validate before production.”

## 14:00-15:00 — Close

Ask for one clear next step:

“Which artifact would be most useful for you to judge: event schema, admin console mock, booking state machine, or growth dashboard spec?”

## Avoid during the call

- Do not recite the whole dossier.
- Do not debate competitors unless he asks.
- Do not lead with compensation or title.
- Do not claim private backend knowledge.
- Do not overfocus on his age.
