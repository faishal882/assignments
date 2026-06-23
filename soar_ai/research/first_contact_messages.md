# First-contact message variants for Henry Langmack

Use the shortest version that fits the channel. The goal is to sound like a builder who noticed the real system, not a candidate sending a generic resume.

## X / DM version

Henry — I dug into Soar and it looks like the hard part is not “flight search,” it’s making booking feel Uber-simple while managing Duffel offers/holds, Stripe-style payment, Twilio/passkeys, booking progress/results, support, fraud, and attribution.

I’ve built similar workflow-heavy infra solo in Tailorec: Next.js + FastAPI + agent/runtime + analytics + AWS ops, plus I built a 32-bit OS from scratch.

If useful, I can send a 1-page teardown on the deal-link → hold → ticketed-booking funnel and the internal tools I’d build first.

## Email / LinkedIn version

Subject: Soar teardown + founding engineer fit

Henry — I spent time studying Soar’s public site, legal pages, and client-route signals. My read: Soar is not just another flight-search UI. The interesting challenge is making booking feel as fast/social as Uber while hiding the operational complexity of Duffel offers, holds, payment, verification, ticketing status, support, fraud, and attribution.

That maps closely to what I’ve built before. I built Tailorec solo across Next.js, FastAPI, agent/browser runtime, analytics, and AWS operations, and scaled it to real traffic. I also built a 32-bit OS from scratch, so I’m comfortable debugging below the framework when needed.

The first thing I’d want to own is measurable: shared fare link → landing → offer selected → hold → payment/ticketed, plus the internal console that makes failed/ambiguous bookings supportable.

If helpful, I can send a short one-page teardown with the first three things I’d ship.

## Ultra-short reply if he asks “what would you build?”

I’d start with the booking/support reliability loop: instrument shared fare → hold → ticketed, then build an internal timeline console for Duffel order state, payment state, verification, user/session context, and support notes. That seems closest to your internal-tools bias and hardest to copy from the outside.

## If he asks “why you?”

Because I’ve already built the adjacent shape: a production Next.js/FastAPI product with external workflows, agent/runtime orchestration, analytics, AWS ops, and user-trust surfaces. I’m not just interested in the UI; I’d want to own the messy booking-state, tooling, and growth-loop layer.
