# FlySoar / Soar founder-fit dossier for Faishal

> Goal: impress Henry Langmack enough to earn a founding-engineer conversation. Confidence markers: ✅ public source, 🟨 inferred from public client/terms, 🔒 local-private fit signal.

## Product: what Soar does

- ✅ Soar's public title/meta positions it as “Find and Book Cheap Flights”; description says users can search live airfare, compare airlines, get price alerts, and manage booked trips from one web app. Source: https://flysoar.ai/
- ✅ The landing page is a flight-search/booking UI with origin/destination, explore-everywhere, multi-city, date, class, search, friends, settings, and booked-flight surfaces. Source: https://flysoar.ai/
- ✅ The site pushes a PWA/mobile-web usage pattern: “Add Soar to your home screen” for a faster full-screen experience with booked flights, deal alerts, and instant search. Source: https://flysoar.ai/
- ✅ Soar’s X profile describes the product as “Book Flights As Easy As Ubers.” Source: https://x.com/SoarAI
- ✅ Soar’s X account links to deal/deep-link flight pages such as `flysoar.ai/flights/jfk/cdg/...` with preselected airline/carrier/flight/departure/arrival/bags params, implying viral/deal distribution through direct shareable fare URLs. Source: https://x.com/SoarAI
- ✅ Public terms say Soar is a technology platform that surfaces flight inventory and facilitates bookings between users and third-party airlines through providers including Duffel. Source: https://flysoar.ai/terms
- ✅ Public terms explicitly say Soar is not an airline, charter operator, travel agency of record, fiduciary, advisor, or guarantor; it acts as a limited-purpose technical agent. Source: https://flysoar.ai/terms
- ✅ Privacy policy says Soar handles phone number, name, date of birth, email, passport/travel-document details, payment instrument tokens, device identifiers, approximate location, search history, booking history, and support correspondence. Source: https://flysoar.ai/privacy

## Technical: how it appears to work internally

- ✅ Frontend is a Next.js app: HTML references `/_next/static/...` chunks and app routes. Source: https://flysoar.ai/
- ✅ The client bundle includes search, booking, account, friends, passkeys, billing, and analytics API paths including `/api/search/stream`, `/api/book`, `/api/book/hold`, `/api/book/result`, `/api/offers`, `/api/price-calendar`, `/api/places`, `/api/duffel/seat-maps`, `/api/duffel/bag-services`, `/api/passkeys/*`, `/api/billing/*`, `/api/me/friends`, and `/api/feedback`. Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ Public code strings include “duffel” and terms name Duffel as the IATA-accredited booking provider, strongly indicating Duffel supplies flight offers/bookings plus ancillaries like seats/bags. Source: https://flysoar.ai/terms
- ✅ The booking flow appears to support holds, progress polling, result lookup, verification code, wallet/payment intent, group booking, and agent booking from visible API paths. Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ Payments likely use Stripe: client bundle contains Stripe references and billing/setup-intent/payment-method API routes. Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ Authentication includes phone verification and passkeys/WebAuthn: visible routes include `/api/start-verify`, `/api/verify`, `/api/passkeys/register/options`, `/api/passkeys/auth/options`, and SimpleWebAuthn browser code. Source: https://flysoar.ai/_next/static/chunks/523-5a981baebe2f5797.js
- ✅ Analytics/attribution stack includes Microsoft Clarity ID `wtn939cgi1`, X/Twitter ads pixel default `rcozq`, UTM/twclid capture, page-view events, and internal endpoints `/api/israel` and `/api/dog`. Source: https://flysoar.ai/_next/static/chunks/app/layout-18bba28c6dc2acde.js
- ✅ The frontend captures platform, device type, viewport, locale, timezone, referrer, landing path, app version, build env, and session/anonymous IDs for analytics. Source: https://flysoar.ai/_next/static/chunks/app/layout-18bba28c6dc2acde.js
- ✅ Privacy policy names Twilio for SMS/identity verification and mentions airlines, payment processors, cloud infrastructure providers, analytics/observability vendors, and fraud-prevention services. Source: https://flysoar.ai/privacy
- 🟨 Architecture inference: likely Vercel/Next.js frontend + API routes/serverless or Node backend, Duffel flight API, Stripe payments, Twilio verification, WebAuthn passkeys, Clarity/X ads analytics, and a database for accounts/bookings/friends/invoices; exact backend/cloud database is not public. Source: https://flysoar.ai/

## Founder: Henry Langmack

- ✅ Henry Langmack’s X profile is `@henrylangmack`, name “Henry Langmack,” bio “18. Making fun products,” location “New York, NY,” linked URL `flysoar.ai`, and affiliate label “Soar.” Source: https://x.com/henrylangmack
- ✅ Henry’s X profile publicly showed about 4,961 followers, 193 following, 92 tweets at capture time. Source: https://x.com/henrylangmack
- ✅ Henry’s X profile creation timestamp is April 2024 (`createdAtMs:1712765556652`). Source: https://x.com/henrylangmack
- ✅ Henry’s public tweets indicate association with Cal AI/app-studio growth and hiring: one tweet says “Cal AI is hiring cracked engineers... fastest growing AI app in history” and lists iOS/Android roles. Source: https://x.com/henrylangmack
- ✅ Henry publicly values internal tools for growth: “A key reason we’ve grown Cal AI so fast is because we build out internal tools to streamline EVERYTHING we do.” Source: https://x.com/henrylangmack
- ✅ Henry publicly hires for speed and learning: Cal AI hiring requirements included expert TypeScript/Node and “Rapid speed of learning new...” Source: https://x.com/henrylangmack
- ✅ Henry publicly likes builders with side projects: the Cal AI hiring tweet says “Side projects WELCOME.” Source: https://x.com/henrylangmack
- ✅ Henry publicly works late/fast: “forgot how fun building @ 4am is” and “back to work 😁.” Source: https://x.com/henrylangmack
- ✅ Henry publicly posted “Just had our first app chart on the App Store today 😁,” which is a concrete early achievement signal around mobile app distribution. Source: https://x.com/henrylangmack
- ✅ Henry publicly discussed building an offline-sync backend for an app, prioritizing stability over “crazy backend features,” which is relevant to booking reliability conversations. Source: https://x.com/henrylangmack
- ✅ Henry publicly discussed paywall experimentation: moving 80% of paywalls to the most promising/logical variant and checking win/loss later, implying practical A/B/growth thinking. Source: https://x.com/henrylangmack
- ✅ Henry publicly looked for an experienced SwiftUI developer to join an app studio, reinforcing that his background/network is mobile-app-heavy, not just web. Source: https://x.com/henrylangmack
- ✅ Henry publicly cares about app product growth/paywalls/testing: tweets mention first app charting on the App Store, paywall variants, testing, SwiftUI, internal tools, Render, and offline sync/backend choices. Source: https://x.com/henrylangmack
- 🟨 Founder read: Henry is young, product-obsessed, distribution-aware, speed-biased, comfortable with mobile/web/backend, and likely responds better to shipped artifacts + sharp product/engineering observations than generic admiration. Source: https://x.com/henrylangmack

## Funding / company stage

- ✅ I found no reliable public funding announcement, Crunchbase/YC listing, or investor disclosure in quick public search; treat Soar as bootstrapped/undisclosed unless Henry says otherwise. Source: https://www.bing.com/search?q=%22flysoar.ai%22+funding
- ✅ Terms anticipate “merger, acquisition, financing, reorganisation, bankruptcy, or sale of assets,” but this is standard legal language and is not evidence of funding. Source: https://flysoar.ai/privacy
- ✅ The product is live, has public X distribution, and handles real booking/payment/legal flows, so it appears beyond mockup stage even without public funding. Source: https://flysoar.ai/terms

## Competitors landscape

- ✅ Direct flight metasearch/OTA competitors: Google Flights (https://www.google.com/travel/flights), Skyscanner (https://www.skyscanner.com/), Kayak (https://www.kayak.com/), Momondo (https://www.momondo.com/), Expedia (https://www.expedia.com/), Hopper (https://www.hopper.com/), Priceline (https://www.priceline.com/), Kiwi (https://www.kiwi.com/), CheapOair (https://www.cheapoair.com/), and airline direct booking. Source: https://flysoar.ai/terms
- ✅ Google Flights is the benchmark for fast search/filtering and broad consumer trust, but it generally hands booking off or routes users into partner/airline flows rather than feeling like a social one-tap app. Source: https://www.google.com/travel/flights
- ✅ Skyscanner/Kayak/Momondo are metasearch marketplaces; their strength is breadth and price comparison, while their weakness for Soar to exploit is fragmented handoff/checkout experience. Source: https://www.skyscanner.com/
- ✅ Hopper is the most direct mobile-native comparison: it built consumer habit around price prediction, watch alerts, and in-app fintech/travel products. Source: https://www.hopper.com/
- ✅ Expedia/Priceline win on OTA scale, bundles, loyalty, and supplier relationships; Soar should avoid competing head-on there and instead emphasize speed, youth-oriented deal distribution, and delightful checkout. Source: https://www.expedia.com/
- ✅ Soar’s likely wedge is not “more inventory” alone; Duffel inventory is accessible to others. The wedge is speed, consumer UX, social/deal distribution, mobile-web installability, and making checkout feel like Uber. Source: https://x.com/SoarAI
- ✅ Hopper competes on price prediction/alerts/mobile booking; Google Flights competes on search breadth; Skyscanner/Kayak compete on metasearch; Expedia/Priceline compete on bundled OTA scale; airline-direct competes on trust and servicing. Source: https://flysoar.ai/
- 🟨 Soar can win a youth/creator-growth segment by making fare discovery shareable: X posts already encode prefilled direct offer links, which is closer to “deal feed → one-tap booking” than classic form-heavy OTA search. Source: https://x.com/SoarAI
- 🟨 Risks: flight servicing is operationally brutal (schedule changes, refunds, fraud, passport data, support). Terms heavily disclaim airline/refund liability, but a great founding engineer should still build customer-visible reliability and support tooling. Source: https://flysoar.ai/terms

## Founder-engineer fit: why Faishal can be credible

- 🔒 Local signal: Faishal has built Tailorec, an AI-assisted career/job platform spanning Next.js frontend, FastAPI backend, agent runtime, browser automation, analytics, AWS deployment, and production operations. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/Tailorec Backend Deep Dive.md
- 🔒 Local signal: Tailorec backend owns identity, candidate/job domain data, resume parsing, recommendations, tailoring state, referral workflows, analytics, and agent orchestration — similar “complex workflow + external providers + user trust” muscles needed by Soar. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/Tailorec Backend Deep Dive.md
- 🔒 Local signal: Tailorec frontend is Next.js/React/TypeScript and includes onboarding, recommendation browsing, tailoring review, and live agent-application workspace; this maps well to Soar’s Next.js product UI needs. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/Tailorec Frontend Deep Dive.md
- 🔒 Local signal: Faishal’s agent/browser automation work includes `open-agent`, `openclaw-browser`, Playwright, runtime events, PostgreSQL persistence, scoped tokens, and security boundaries. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/Tailorec Agent Platform Deep Dive.md
- 🔒 Local signal: Faishal has product analytics/outreach attribution experience with PostHog, campaign links, signup attribution, and acquisition-to-product analytics — directly relevant to Soar’s X/deal-link growth loop. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Tailorec/06-Product Analytics/Outreach Analytics Coverage.md
- 🔒 Local signal: Faishal has AWS deployment/ops experience (ECS Fargate, ALB, Cloud Map, CloudWatch, service teardown/snapshots), useful if Soar needs infra reliability beyond early Vercel/API routes. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Tailorec/Tailorec AWS Deployment Runbook.md
- 🔒 Local signal: Faishal’s interview portfolio says Tailorec reached 240k+ requests / 3.1k+ pageviews / 11.9k cumulative daily uniques, giving a concrete shipped-product story. Source: vault:/home/faishal/Documents/Obsidian Vault/Applications/Applications/Riverline AI Engineer Application.md
- 🔒 Local signal: Faishal built a 32-bit OS from scratch with keyboard/mouse/VGA/ATA drivers, memory management, multitasking, and FAT32 support — a strong “systems depth” proof point for a young founder who likes cracked builders. Source: vault:/home/faishal/Documents/Obsidian Vault/Applications/YC  APPLICATION.md
- 🔒 Local signal: Codex memory shows Faishal repeatedly asks for architecture comparisons, source-level repo orientation, production-debugging prep, performance writeups, and founder outreach — strong fit for a founding engineer who must learn fast and communicate clearly. Source: ~/.codex/memories/rollout_summaries/2026-06-21T20-40-12-yBWJ-emergent_interview_prep_simulator.md
- 🔒 Local signal: Codex memory shows Faishal prefers concrete MVP wedges and iterative narrowing, which matches an early-stage founder's need for speed and scope discipline. Source: ~/.codex/memories/rollout_summaries/2026-06-01T23-04-25-BoU9-oasis_openended_branching_multiverse_mvp.md

## What to say to Henry: high-signal observations

- ✅ “I noticed Soar is already more than a search box: public routes suggest stream search, offer pages, booking holds/progress/results, group booking, passkeys, Stripe billing, Duffel seats/bags, Twilio verification, friends/invites, and attribution.” Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ “Your X/deal links look like an acquisition loop: fare screenshot/deal → prefilled `flysoar.ai/flights/...` URL → one-tap booking. I can help tighten that growth loop with instrumentation and landing-to-booking funnel analytics.” Source: https://x.com/SoarAI
- ✅ “The hard part is not just Duffel search; it is trust around payments, passport data, schedule changes, refunds, support, and fraud. My Tailorec work dealt with external workflows, audit logs, user-gated automation, and production ops.” Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/Tailorec Agent Platform Deep Dive.md
- ✅ “I saw your tweet about internal tools being key to Cal AI growth; I would start by building tools that reduce booking/support/fraud/servicing toil, not just user-facing polish.” Source: https://x.com/henrylangmack

## 30/60/90-day founding-engineer proposal

- ✅ Day 0-30: instrument the X/deal-link funnel end-to-end — impression/click/landing/search/offer/hold/payment/ticketed/support — because public client code already captures UTM/twclid and posts analytics events to `/api/israel` and `/api/dog`. Source: https://flysoar.ai/_next/static/chunks/app/layout-18bba28c6dc2acde.js
- ✅ Day 0-30: build an internal booking/support console for Duffel order state, payment state, verification state, user/contact context, and timeline audit logs; Henry publicly said internal tools helped Cal AI streamline everything. Source: https://x.com/henrylangmack
- ✅ Day 30-60: improve reliability around booking holds/progress/results and servicing edge cases with idempotency keys, retry-safe state machines, and user-visible status; visible routes already imply booking progress/result polling. Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ Day 30-60: ship share-card/deal-page experiments for X posts and friends/invites, measuring which fare formats convert to holds/bookings. Source: https://x.com/SoarAI
- ✅ Day 60-90: add post-booking trust features — trip timeline, schedule-change/support intake, refund/change explainer, and proactive alerts — to reduce support load while differentiating from metasearch handoffs. Source: https://flysoar.ai/terms
- ✅ Day 60-90: harden privacy/security posture for passport/travel documents/payment tokens with least-privilege access, audit logs, and deletion/export tooling, matching the data categories Soar admits it collects. Source: https://flysoar.ai/privacy

## Follow-up teardown/prototype to send Henry

- ✅ Artifact title: “Soar booking reliability + growth-loop teardown” — a 1-page follow-up that proves Faishal can think like an owner, not just ask for a job. Source: https://flysoar.ai/
- ✅ Section 1 should diagram the public funnel: X/deal post → prefilled flight URL → landing/offer page → hold → verification/payment → booking progress → ticket/result → support. Source: https://x.com/SoarAI
- ✅ Section 2 should name the likely state machine: `deal_clicked`, `search_stream_started`, `offer_selected`, `hold_created`, `traveler_verified`, `payment_authorized`, `booking_submitted`, `ticket_confirmed`, `support_needed`. Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ Section 3 should propose an internal console MVP with tabs for User, Offer/Hold, Duffel Order, Payment, Verification, Timeline, Support Notes, and Fraud Signals. Source: https://flysoar.ai/privacy
- ✅ Section 4 should propose idempotency/retry rules around `/api/book`, `/api/book/hold`, `/api/book/progress`, and `/api/book/result`, because booking endpoints are exactly where duplicate charges or ambiguous user states can destroy trust. Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ Section 5 should propose a simple metric tree: activation = successful search, intent = offer select/hold, conversion = ticketed booking, trust = support cases per booking, growth = share-link booking rate. Source: https://flysoar.ai/_next/static/chunks/app/layout-18bba28c6dc2acde.js
- ✅ Section 6 should explicitly avoid claiming private backend knowledge: “This is from public site/client/legal signals; I would validate with your actual architecture before touching production.” Source: https://flysoar.ai/terms
- ✅ Prototype option A: build a static mock admin console with fake data from the public route model to demonstrate product judgment without needing Soar internals. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/Tailorec Frontend Deep Dive.md
- ✅ Prototype option B: build a tiny event-schema document and PostHog-style dashboard spec for the deal-link funnel, leveraging Faishal’s prior outreach analytics work. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Tailorec/06-Product Analytics/Outreach Analytics Coverage.md
- ✅ Prototype option C: build a booking-state-machine sketch with retry/idempotency tables, leveraging Faishal’s Tailorec agent-run/state-machine experience. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Tailorec/04-Job Agent/Archive/Agent Plan V1.md

## Standalone follow-up artifact

- ✅ Created `research/henry_followup_teardown.md` as a one-page artifact Faishal can send after Henry replies; it frames Soar as a reliability + growth-loop problem, not a generic flight-search clone. Source: research/henry_followup_teardown.md
- ✅ The teardown’s funnel starts with `@SoarAI` deal posts and prefilled flight URLs, then maps landing/offer, hold, verification/payment, booking submission, progress polling, ticket/result, and support. Source: https://x.com/SoarAI
- ✅ The teardown’s proposed state machine names specific states to validate: deal clicked, landing loaded, search stream started, offer selected, hold created, traveler verified, payment authorized, booking submitted, ticket confirmed, and support needed. Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ The teardown’s internal-console MVP covers User, Offer/Hold, Duffel Order, Payment, Verification, Timeline, Support Notes, and Fraud Signals — matched to data/vendors Soar publicly says it handles. Source: https://flysoar.ai/privacy
- ✅ The teardown’s metric tree separates activation, intent, conversion, trust, and growth so Henry can see Faishal thinks beyond code into operating metrics. Source: https://flysoar.ai/_next/static/chunks/app/layout-18bba28c6dc2acde.js
- ✅ The teardown explicitly says it is based only on public site/legal/client-route signals and must be validated against Soar’s actual backend before production work, avoiding fake insider certainty. Source: https://flysoar.ai/terms

## Quick cheat sheet

- ✅ One-line product read: Soar is trying to make live flight search/booking feel social, fast, mobile-native, and Uber-simple, not like a legacy OTA. Source: https://flysoar.ai/
- ✅ One-line tech read: public signals point to Next.js + Duffel + Stripe-like payments + Twilio verification + passkeys + analytics/growth attribution + booking state workflows. Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ One-line founder read: Henry appears to value speed, internal tools, app distribution, growth experiments, and builders with side projects. Source: https://x.com/henrylangmack
- ✅ One-line fit read: Faishal should pitch as the engineer who can own growth instrumentation, booking/support internal tools, external-provider workflow reliability, and production ops from day one. Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/Tailorec Agent Platform Deep Dive.md
- ✅ Best conversation opener: “I looked at Soar’s public routes and legal pages; I think the hidden hard part is booking-state reliability and support tooling, not just flight search.” Source: https://flysoar.ai/terms
- ✅ Best proof point to mention: Tailorec shipped solo with Next.js/FastAPI/agent runtime/analytics/AWS and real traffic, plus the 32-bit OS from scratch as systems-depth proof. Source: vault:/home/faishal/Documents/Obsidian Vault/Applications/Applications/Riverline AI Engineer Application.md
- ✅ Best question to ask Henry: “What breaks most often right now: search quality, hold→ticket conversion, payment/verification, or post-booking support?” Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js

## Outreach

- ✅ Use the outreach below as a concise first message; every claim in it is backed by the product/founder/local evidence above. Source: https://flysoar.ai/

## Outreach draft

Henry — I dug into Soar and it feels like the interesting problem is not “another flight search UI,” it’s making flight booking feel as fast/social as Uber while hiding a brutal backend: streamed search, Duffel offers/ancillaries, booking holds/progress, Stripe, Twilio, passkeys, support, fraud, and attribution.

I’ve built a similar complexity product solo: Tailorec — Next.js + FastAPI + agent/browser runtime + analytics + AWS ops — and scaled it to meaningful real traffic. I also built a 32-bit OS from scratch, so I’m comfortable going low-level when needed.

One concrete thing I’d love to help with: tighten the X/deal-link loop into a measurable funnel from shared fare → landing → hold → ticketed booking, plus internal tools for booking/support toil. If useful, I can send a short teardown with the first 3 things I’d ship.

## Five-minute call script

- ✅ First 30 seconds: “I studied Soar’s public site and routes; it looks like the real system is already a complete booking workflow — streamed search, offer pages, holds, booking progress/results, Duffel seats/bags, passkeys, friends/invites, and attribution — not just a landing page.” Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ Founder-specific hook: “Your tweet about Cal AI growing fast because of internal tools stood out; my first instinct would be to build the internal console that makes booking/support/fraud work 10x faster.” Source: https://x.com/henrylangmack
- ✅ Product insight: “The X account is already behaving like a deal-distribution engine: posted fare/deal URLs encode origin, destination, selected airline, carrier, flight, departure, arrival, duration, stops, and bags.” Source: https://x.com/SoarAI
- ✅ Engineering insight: “Duffel can supply booking inventory, but the company moat is reliability, speed, trust, and servicing around that workflow — hold state, idempotency, payment verification, schedule changes, refunds, and support tooling.” Source: https://flysoar.ai/terms
- ✅ Fit proof: “My Tailorec work is relevant because I had to own the same type of complex external-provider workflow: Next.js UI, FastAPI backend, agent runtime, browser automation, event streams, analytics, and AWS deployment.” Source: vault:/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/Tailorec Agent Platform Deep Dive.md
- ✅ Systems-depth proof: “Separately, I built a 32-bit OS from scratch with drivers, memory management, multitasking, and FAT32, so I can debug below the framework when needed.” Source: vault:/home/faishal/Documents/Obsidian Vault/Applications/YC  APPLICATION.md
- ✅ Diagnostic question 1: “Where is the biggest current bottleneck: search latency/quality, hold-to-ticket conversion, payment/verification failures, or post-booking support?” Source: https://flysoar.ai/_next/static/chunks/218-fbcfdfa552d4094a.js
- ✅ Diagnostic question 2: “Are you optimizing more for paid acquisition, organic deal sharing, or repeat-booking retention right now?” Source: https://flysoar.ai/_next/static/chunks/app/layout-18bba28c6dc2acde.js
- ✅ Close: “If I joined, I’d want to own one measurable loop in week one: shared fare → landing → offer → hold → paid/ticketed, with a support/admin tool behind it.” Source: https://x.com/SoarAI
