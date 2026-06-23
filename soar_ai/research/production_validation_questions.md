# Production validation questions before touching Soar code

These are the questions Faishal should ask after earning technical trust. They turn public-signal hypotheses into implementation-safe work.

## Booking state

- What are the canonical booking states from offer search through ticket confirmation?
- Which states can be retried safely, and which require operator review?
- What is the source of truth for hold expiry, booking progress, and ticket status?
- Which booking states are user-visible versus internal-only?

## Provider boundaries

- Which Duffel objects and IDs are stored locally: offers, orders, passengers, services, seats, bags, payment references?
- Where does Soar wrap provider errors into user-facing messages?
- Which provider webhooks or polling paths are authoritative?
- What is the fallback when Duffel and local state disagree?

## Payments and idempotency

- What idempotency keys exist across hold, book, payment intent, capture, refund, and result polling?
- What happens if payment succeeds but ticketing fails or times out?
- What is the operator playbook for duplicate charges, expired holds, or partial provider failures?
- Which events are safe to replay?

## Verification and traveler data

- What traveler/passport fields are required before hold versus before booking?
- Which verification failures block payment, and which only block ticketing?
- Who can view sensitive traveler data internally, and is access audited?

## Support operations

- What does support need to see in the first 30 seconds of a booking issue?
- Which support actions are currently manual and repeated?
- Are refunds/changes handled inside Soar, handed off to airlines/Duffel, or triaged case-by-case?

## Growth instrumentation

- What are the current funnel events from shared fare/deal link to ticketed booking?
- Are UTM/twclid/referrer fields connected to booking outcomes?
- Which metric matters most this month: search activation, hold rate, payment completion, ticketed booking, repeat booking, or support reduction?

## Security and privacy

- Which logs may contain PII, passport data, payment references, or support transcripts?
- What is the data deletion/export path and who owns it operationally?
- Which admin actions need audit trails before an internal console is safe?
