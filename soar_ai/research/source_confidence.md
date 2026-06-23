# Source confidence map

Use this to decide how strongly to phrase each claim when talking to Henry.

## High confidence: safe to state directly

- Soar is a live flight-search/booking web app; the public title, meta description, UI, terms, and privacy policy all support this.
- Soar terms explicitly name Duffel as an IATA-accredited booking provider.
- Soar terms state it is a technology platform and not an airline, charter operator, travel agency of record, fiduciary, advisor, or guarantor.
- Soar privacy policy says it collects travel-document, payment-token, device, search-history, booking-history, support, and verification-related data.
- Henry’s public X profile links to flysoar.ai and describes him as “18. Making fun products.”
- Henry has publicly posted about internal tools, Cal AI hiring, app growth, SwiftUI, offline sync, and paywall experimentation.

## Medium confidence: phrase as public-signal inference

- Soar likely uses Stripe or Stripe-like payment flows, because public client routes/code reference billing, setup intents, payment methods, wallet payment intents, and Stripe strings.
- Soar likely has a sophisticated booking state workflow because public routes include hold, progress, result, verification code, group booking, and booking endpoints.
- Soar likely cares about X-driven acquisition because public code captures `twclid` and X ads pixel data, and the public X account posts fare/deal links.
- Soar’s wedge is likely speed/social deal distribution/one-tap booking rather than proprietary inventory, because terms name Duffel and public X links expose deal-style routes.

## Low confidence or unknown: do not claim

- Funding status beyond “undisclosed / no reliable public announcement found.”
- Backend database, cloud provider, team size, revenue, conversion metrics, or exact provider contracts beyond named public vendors.
- Whether Henry personally wrote specific parts of Soar unless he says so.
- Whether Soar is currently hiring for founding engineers unless a direct source confirms it.

## Best phrasing rule

- Use “is” for public terms/profile/site facts.
- Use “appears,” “public signals suggest,” or “my hypothesis” for client-route and product-strategy inferences.
- Use “unknown” or “undisclosed” for funding/team/private backend claims.
