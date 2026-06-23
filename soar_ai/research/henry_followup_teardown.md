# Soar booking reliability + growth-loop teardown

> Draft artifact Faishal can send after a first reply from Henry. It is intentionally based only on public signals, not private backend access.

## Thesis

Soar’s opportunity is not just cheaper flight search. The interesting wedge is making travel booking feel as fast, social, and low-friction as Uber while quietly solving the trust-heavy operational problems behind tickets, payments, traveler verification, support, and schedule/refund edge cases.

## Public-signal funnel

```text
X/deal post
  → prefilled flysoar.ai/flights/... URL
  → offer/landing page
  → hold or selected offer
  → traveler verification + payment
  → booking submission
  → progress polling
  → ticket/result
  → post-booking support / trip management
```

Public signals behind this: Soar posts prefilled fare URLs from `@SoarAI`; the client bundle exposes booking routes including search stream, book, hold, progress, result, wallet/payment intent, Duffel seat maps, and bag services; terms name Duffel as the booking provider.

## State machine I would validate first

- `deal_clicked`
- `landing_loaded`
- `search_stream_started`
- `offer_selected`
- `hold_created`
- `traveler_verified`
- `payment_authorized`
- `booking_submitted`
- `ticket_confirmed`
- `support_needed`

The point is to remove ambiguous states: duplicate booking attempts, payment succeeded but ticket status unclear, hold expired after user intent, or support lacking enough timeline context.

## Internal console MVP

Tabs I would build first:

1. **User** — account, contact, verification, recent sessions.
2. **Offer / Hold** — selected offer, expiry, price, bags/seats.
3. **Duffel Order** — provider IDs, status, raw event timeline.
4. **Payment** — authorization/capture/refund state, idempotency key.
5. **Verification** — phone/passkey/traveler-document status.
6. **Timeline** — every user-visible and backend event in order.
7. **Support Notes** — operator notes and canned next actions.
8. **Fraud Signals** — device/session/IP/payment mismatch flags.

## Metric tree

- Activation: successful search / offer-page load.
- Intent: offer selected or hold created.
- Conversion: ticketed booking.
- Trust: support cases per booking, ambiguous booking states, refund/change escalations.
- Growth: share-link click → hold → ticketed booking rate.

## First week implementation slice

Ship one measurable loop: `shared fare → landing → offer selected → hold → payment/ticketed`, with event instrumentation and a minimal admin timeline for failed/ambiguous bookings.

## Caveat

This teardown is based on public site, legal pages, and public client-route signals. I would validate the actual backend architecture, provider contracts, and incident history with Henry before touching production.
