# Likely founder objections and concise answers

Use these only if Henry raises the concern. Keep answers short, then redirect to a concrete shipping offer.

## “Do you know travel?”

Not deeply yet, but I understand the shape of the hard problem: external-provider workflows, user trust, payments, identity/verification, support state, analytics, and operational tooling. I would learn Duffel/travel specifics fast by owning one narrow loop: shared fare → hold → ticketed booking → support timeline.

## “Why should I trust you with production?”

I would not ask for broad production access on day one. I would start with read-only logs/events, a shadow dashboard, or a fake-data admin-console prototype, then graduate to low-risk instrumentation and internal tooling once the actual architecture is validated.

## “Can you move fast enough?”

Yes. My strongest proof is that I build end-to-end: frontend, backend, agent/runtime, analytics, deployment, and docs. For Soar, I would propose a 48-hour artifact first: event schema + funnel dashboard spec + fake-data booking timeline console.

## “What if we already have this internally?”

Then I would ask where the pain actually is: search latency, hold expiry, payment/verification failures, support operations, fraud, or retention. The goal is not to force my teardown; it is to find the highest-leverage bottleneck and own it.

## “Are you just reverse-engineering client routes?”

No. Public routes are only enough to form hypotheses. The real value is how I translate them into product/ops questions, risk areas, metrics, and prototype plans while explicitly avoiding claims about private internals.

## “What would you ship in 48 hours?”

1. A public-signal funnel/event schema.
2. A fake-data booking timeline/admin console mock.
3. A metric tree for shared fare → hold → ticketed.
4. A short list of production questions I need answered before implementation.

## “What role do you want?”

Founding engineer / full-stack product engineer. I would be happiest owning the messy layer between growth, backend reliability, user trust, internal tools, and support operations.
