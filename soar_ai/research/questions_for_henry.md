# High-signal questions to ask Henry

Use only 2-3 of these in a real conversation. The goal is to learn where Soar actually hurts, not to show off research.

## Product / growth

1. Which loop matters most right now: paid acquisition, organic deal sharing, repeat booking, or referrals/friends?
2. For shared fare links, where is the biggest drop-off: click → landing, landing → offer, offer → hold, hold → payment, or payment → ticketed?
3. Are users mostly coming for one-off cheap deals, or are you trying to build a repeat travel-booking habit?

## Booking reliability

4. What is the most common ambiguous state today: hold expired, payment authorized but ticket unclear, provider timeout, traveler verification issue, or airline schedule/refund problem?
5. How do you currently reason about idempotency across `/book`, hold, payment, and result/progress polling?
6. What booking failure would make you drop everything if it happened twice in a day?

## Internal tools / operations

7. If you had one internal console tomorrow, should it optimize support speed, fraud triage, payment debugging, Duffel order visibility, or growth funnel analysis?
8. What information does support/operator work currently lack when a booking goes wrong?
9. Which manual workflow do you repeat enough that it deserves an internal tool this week?

## Founder / team fit

10. Do you want a founding engineer to bias more toward product velocity, backend reliability, growth instrumentation, or operational tooling in the first month?
11. What does “cracked engineer” mean to you in practice: raw speed, taste, low-level debugging, shipping without specs, or growth ownership?
12. If I did a 48-hour no-access artifact, what would be most useful to judge: event schema, fake-data admin console, booking state machine, or growth dashboard spec?

## Best three-question sequence

If time is short, ask these:

1. “Where is the biggest current bottleneck: shared-link conversion, hold-to-ticket reliability, payment/verification ambiguity, or post-booking support?”
2. “What internal tool would save you the most time this week?”
3. “If I built a 48-hour fake-data artifact, which would be most useful for you to evaluate?”
