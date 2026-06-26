# FlySoar / Soar Founding Engineer Brief

Research date: 25 June 2026 (IST)  
Target: a high-signal conversation with Henry Langmack about a founding-engineer role  
Product: [flysoar.ai](https://flysoar.ai/)

## Bottom line

Soar is a very new, founder-led consumer flight search and booking product. Its public launch signal dates to 19 May 2026. The wedge is not merely “find cheap flights.” It is removing the handoffs and form repetition between search, traveler details, payment, ticketing, group coordination, and post-booking support.

The product already exposes a surprisingly broad transaction surface: live flight search, flexible dates, multi-city and “everywhere” discovery, direct booking, saved cards and traveler documents, friends/group booking, seat and bag selection, booking verification, trip management, changes/refunds, price alerts, auto check-in, and flight-status messaging.

The strongest verified technical signals are Next.js, a same-origin API, streamed search results, Duffel inventory/ticketing, Stripe payments, Twilio-based messaging/verification, WebAuthn passkeys, Cloudflare, and Render. There is no public evidence that the core search path is powered by an LLM. The `.ai` domain is not proof of an AI architecture.

The most important correction to the initial premise: public evidence clearly identifies Alex Slater as a founder and launch voice for FlySoar. Henry's LinkedIn associates him with Soar, and the product says users can contact “the founders,” but the sources reviewed do not independently expose Henry's exact Soar title. Do not lead with “I researched you as Soar's founder.” Say “what you're building at Soar.”

For Faisal, the credible fit is end-to-end execution under messy state: product UI, APIs, payments/integrations, cloud infrastructure, event-driven workflows, agent/browser orchestration, observability, and production debugging. The pitch should not be “I love travel” or “I know AI.” It should be: **I have already built systems where unreliable external workflows, sensitive data, async state, retries, and user approvals have to behave like one reliable product.**

## Evidence standard

- **Verified:** directly visible on Soar's live site, legal pages, response headers, public client assets, or a named primary/reputable source.
- **Strong inference:** multiple public implementation signals point to the conclusion, but server source is not public.
- **Unknown:** no reliable public evidence was found. Unknown is not the same as false.
- Public client assets were inspected only to understand product architecture. This brief does not include secrets, exploit instructions, or attempts to access protected data.

## 1. What Soar does

### Core job to be done

Soar tries to compress flight shopping and booking into one fast web experience:

1. Enter origin, destination, dates, passengers, and cabin.
2. Receive live offers rather than a static redirect page.
3. Compare results by best, price, or duration and filter by stops, airline, and time.
4. Open an offer, choose seats/bags where available, and supply traveler data.
5. Pay and ticket without being passed through multiple airline/OTA pages.
6. Manage the booking, check-in, changes, cancellation/refund requests, alerts, and group participants afterward.

The homepage metadata describes it as: “Find and book cheap flights instantly with Soar. Search live airfare, compare airlines, get price alerts, and manage booked trips from one web app.” The PWA manifest repeats live airfare search, deal alerts, and trip management.

### Visible product surface

Verified on the live application or its public interface:

- One-way, round-trip, and multi-city search.
- Origin/destination by city or airport, including region/multi-airport searches.
- “Explore everywhere” and country/city discovery.
- Flexible-date windows from exact dates to ±14 days.
- Economy, premium economy, business, and first.
- Result sorting by best, price, and duration.
- Stops, airlines, and departure/arrival time filters.
- Search-result streaming and reconnect behavior.
- Directly bookable offers plus non-bookable/deep-link offers.
- Split-ticket awareness.
- Saved traveler identity and passport information.
- Saved cards, Stripe setup intents, and payment methods.
- Friends, managed travelers, invites, and group booking flows.
- Seat-map and bag-service selection for Duffel offers.
- Booking verification codes and idempotent booking requests.
- Booking progress, confirmation, invoices, and trip history.
- Change quotes, cancellation quotes, refund requests, and withdrawal of refund requests.
- Refund-protection upsell when eligible.
- Price alerts and booked-trip notifications.
- Auto check-in and boarding-pass messaging are promised in the activation flow.
- Passkey authentication using Face ID, Touch ID, or hardware security keys.
- Installable PWA behavior on iPhone and Android.
- Founder-direct support, email support, and 24/7 phone support are advertised.

### Business position

Soar's Terms say it is a technology platform that surfaces inventory and facilitates airline bookings through third-party providers, including Duffel. It says Soar is not the airline, charter operator, travel agency of record, fiduciary, advisor, or guarantor. The operating carrier remains the counterparty for the flight.

That legal position matters technically: Soar owns the customer experience and orchestration but depends on supplier inventory, airline rules, and payment/ticketing state it does not fully control.

## 2. How the technology appears to work

### High-level architecture

```text
Browser / installable web app
        |
        | Next.js UI + same-origin API calls
        v
Cloudflare edge
        |
        v
Render-hosted Next.js application
        |
        +--> search aggregation / sorting / fare freshness
        |       |
        |       +--> Duffel and possibly other offer sources
        |
        +--> booking orchestration
        |       +--> Duffel ticketing / ancillaries
        |       +--> Stripe payment intents / saved methods
        |
        +--> identity and messaging
        |       +--> Twilio verification / SMS signals
        |       +--> WebAuthn passkeys
        |
        +--> traveler, friend, booking, invoice, and alert state
                +--> database vendor is not publicly identifiable
```

### Search path

The browser sends a JSON `POST` to `/api/search/stream`. The response is consumed as a readable stream using Server-Sent Events-style frames. Public client logic handles event types such as an offer, an error, and completion/status events. Offers are progressively appended instead of waiting for the entire search to finish.

This design improves perceived speed but creates hard engineering requirements:

- duplicate suppression and stable offer identity;
- cancellation when the user changes search parameters;
- reconnect and partial-result behavior;
- supplier timeout isolation;
- sorting while results are still arriving;
- fare freshness and repricing before payment;
- comparable normalization across providers and currencies;
- detecting off-route, split-ticket, or non-bookable results.

The client contract includes total/base/tax amounts, currencies, carrier data, segments, baggage, terminals, time zones, fare brands, conditions, provider, booking provider, Google Flights URL, and split-ticket metadata. This indicates a normalization layer between raw provider responses and the UI.

### Offer and checkout path

Public signals support this likely sequence:

1. User selects an offer.
2. Soar fetches/revalidates offer details.
3. For Duffel-backed inventory, it can request seat maps and bag services.
4. Soar validates traveler completeness, including passport requirements for international routes.
5. A saved card or new Stripe payment method is selected.
6. The booking request includes an idempotency key to prevent duplicate ticketing on retries.
7. If additional card authentication/payment action is required, the API returns a Stripe PaymentIntent client secret and the client completes the payment step.
8. The application tracks booking progress and returns a final confirmation or a structured failure.
9. The booking is then available for trip management, invoices, check-in, changes, cancellation, and refund workflows.

The application explicitly handles fare drift, card declines, provider failures, cancellation, booking progress, and split-ticket offer IDs. This is real transaction-orchestration work, not a simple affiliate redirect.

### Identity and sensitive data

Verified signals:

- Phone verification endpoints and Twilio named in the Privacy Policy.
- Email start/verify flows.
- WebAuthn registration/authentication endpoints and SimpleWebAuthn client code.
- Cookie-included API requests rather than a public bearer token exposed in the UI.
- Saved personal details, date of birth, passport, known-traveler number, cards, friends, and managed travelers.
- A separate booking verification-code step.

This product therefore handles high-value PII and payment-adjacent data. Its Privacy Policy says it may collect passport/travel documents, payment tokens, device identifiers, IP/location data, search and booking history, and support correspondence. It names airlines, Duffel, payment processors, Twilio, infrastructure, analytics, observability, fraud-prevention, and professional-service providers as data recipients.

### Post-booking and “Sky” activation

The UI contains an activation flow that asks the user to send a text in order to unlock:

- flight alerts;
- gate changes;
- baggage-pickup/status updates;
- automatic check-in;
- boarding passes sent to the user.

Public routes include a “sky activated” state. This looks like a messaging-based travel companion layered over bookings. Whether it uses an LLM is unknown. The defensible statement is that it connects a phone/SMS channel to booking and flight-event automation.

### Frontend and platform signals

| Layer | Evidence | Confidence |
| --- | --- | --- |
| Web framework | Next.js app assets and `x-powered-by: Next.js` | Verified |
| UI runtime | React/Next app-router bundles | Verified |
| Validation | Zod schemas visible in client contract code | Verified |
| Search transport | `POST /api/search/stream` with streamed event parsing | Verified |
| Flight inventory/ticketing | Duffel named in Terms/Privacy and dedicated seat/bag routes | Verified |
| Payments | Stripe JS, setup intents, saved methods, PaymentIntent handling | Verified |
| SMS/verification | Twilio named in Privacy; phone verification UI/API | Verified |
| Passkeys | WebAuthn endpoints and SimpleWebAuthn client | Verified |
| Edge | Cloudflare response headers | Verified |
| Hosting | Render response header and DNS target; GCP us-west Render origin | Verified |
| Maps/location | Google Maps loader and IP geolocation client signals | Verified |
| Analytics | Microsoft Clarity and X/Twitter advertising/attribution signals | Verified |
| PWA | Web manifest and add-to-home-screen flow | Verified |
| Database | No reliable public vendor signal | Unknown |
| Queue/workflow engine | No reliable public vendor signal | Unknown |
| LLM/model provider | No OpenAI/Anthropic/Gemini evidence in the reviewed live path | Unknown |

### Public API surface categories

The client calls APIs for:

- search, places, price calendars, explore prices, currencies;
- offers, Duffel seats/bags, booking holds, booking progress and results;
- Stripe billing config, setup intents, payment methods, wallet payment intents;
- bookings, change/cancellation/refund/check-in operations;
- authentication, phone/email verification, passkeys, logout;
- profile, friends, managed travelers, requests and invitations;
- invoices, support, feedback, referrals, and alerts/activation.

This is best described as a modular monolith or a same-origin backend-for-frontend from public behavior. It may use internal services, but the external evidence does not prove microservices.

## 3. The hard engineering problems inside Soar

### 1. Booking correctness

Search can tolerate stale or partial data; ticketing cannot. The system must reconcile four moving states:

- what the search result promised;
- what the airline/provider can still sell;
- what Stripe authorized/captured;
- what was actually ticketed.

Retries, timeouts, and browser refreshes must never create duplicate charges or duplicate tickets. Idempotency helps, but the backend also needs a durable booking state machine, reconciliation jobs, and operator tooling.

### 2. Fare freshness and normalization

“Cheapest” only works if fares are comparable. Baggage, cabin/fare brand, self-transfers, split tickets, taxes, payment fees, and refundability can make a nominally cheap itinerary worse. Ranking must balance price, duration, stops, protection, and booking confidence.

### 3. Supplier dependence

Duffel is a strong speed-to-market choice because it provides IATA-accredited access and booking APIs, but a single primary supplier creates coverage, pricing, outage, and negotiating risk. The client already understands offers that are not directly bookable, suggesting Soar may mix bookable and metasearch-style inventory.

### 4. Sensitive data and trust

The product stores identity and travel documents for convenience. That is a powerful retention loop and a serious security obligation. Field-level encryption, strict internal access, audit logs, data minimization, verified deletion, incident response, and vendor risk become founding-engineer concerns immediately.

The reviewed top-level responses did not expose common browser security headers such as a Content-Security-Policy or Strict-Transport-Security header. This is not proof of a vulnerability, but it is a concrete reason to run a deliberate application-security/header review before scale.

### 5. Post-booking operations

Search is the acquisition surface; support is where trust is won or lost. Schedule changes, cancellations, refunds, check-in failures, and carrier outages require automation plus an operator console. “Text a cofounder” is excellent early-stage customer discovery but not a scalable support architecture.

### 6. Group travel

Friends and managed travelers can be a genuine differentiator, but they multiply complexity: consent, identity ownership, who pays, separate vs shared bookings, synchronized fare availability, invite state, partial failure, and privacy boundaries.

## 4. Product and business model

### Likely revenue paths

Public evidence does not disclose the revenue model. Plausible paths are:

- booking/service margin or commission on directly ticketed flights;
- ancillary revenue from seats, bags, and protection products;
- payment/fintech economics;
- future memberships or premium travel automation;
- affiliate revenue for non-bookable offers/deep links.

Treat these as hypotheses until Henry confirms them.

### Real moat thesis

Flight search alone is not defensible against Google Flights, Skyscanner, KAYAK, or airline-direct inventory. The more credible moat is a compound workflow:

1. A faster interface earns the first search.
2. Stored travelers/cards make the second booking much faster.
3. Friends/group coordination brings in other users.
4. Alerts, check-in, changes, and support retain the traveler after purchase.
5. Booking and support outcomes generate proprietary reliability/ranking data.

The valuable data is not merely “which fare was cheap.” It is which offers repriced, failed payment, failed ticketing, produced support load, or resulted in a satisfied trip. That can improve ranking and supplier routing over time.

## 5. Competitor landscape

### Direct consumer competitors

| Competitor | Strength | Where Soar can differ | Main threat to Soar |
| --- | --- | --- | --- |
| Google Flights | Speed, coverage, flexible-date graphs, “best/cheapest,” price tracking, distribution | Complete booking and post-booking relationship in one product | Google owns search intent and can copy interface improvements |
| Skyscanner | Broad metasearch, “Everywhere,” month/year flexibility, alerts, global brand | Avoid redirect/OTA handoff; make booking and support consistent | Enormous inventory breadth and mature international demand |
| KAYAK | Metasearch, Explore, flexible dates, alerts, rich filters | Cleaner flow, saved travelers, group coordination, direct support | Established comparison UX and Booking Holdings distribution |
| Hopper | Mobile booking, price prediction, watches, price freeze and protection products | Faster web/PWA experience and social/group workflow | Strong fintech/ancillary product set and prediction data |
| Expedia / Booking.com / Priceline | Full-trip bundling, loyalty, support infrastructure, supply relationships | Focused flight UX without cross-sell clutter | Scale, capital, support operations, and bundling economics |
| Kiwi.com | Virtual interlining and unusual low-cost combinations | Better trust, simpler policies, direct bookability | Can surface routes traditional inventory misses |
| Going | Curated deal alerts and strong traveler trust/content | Transaction and trip-management layer rather than alerts alone | Owns “tell me when a great deal appears” behavior |
| Airline-direct apps | Highest booking trust and direct servicing | Cross-airline comparison and one reusable traveler profile | Travelers often prefer airline-direct handling when disruption happens |

### Infrastructure and adjacent players

- **Duffel:** primarily an enabling supplier/API, not a consumer competitor. Dependency and strategic partner.
- **Amadeus, Sabre, Travelport:** distribution/inventory infrastructure and potential future supplier alternatives.
- **Stripe:** payments infrastructure, not a travel competitor.
- **Navan / TravelPerk:** business-travel workflow competitors if Soar moves into managed corporate travel.
- **Point.me / Roame:** adjacent if Soar expands into award travel.

### Soar's current differentiation

Verified or strongly indicated:

- fewer handoffs between search and ticketing;
- one-page, speed-focused consumer UX;
- reusable traveler/payment identity;
- group/friend booking mechanics;
- post-booking messaging and auto check-in ambition;
- founder-direct support and fast iteration;
- direct bookability for supported inventory.

### Weaknesses to expect

- much smaller supply and brand trust than incumbents;
- supplier and airline servicing dependence;
- 24/7 operational burden after taking payment;
- security/compliance exposure from passport and payment-adjacent data;
- potentially thin margins and high support cost;
- interface speed is copyable unless backed by workflow/data advantages;
- unclear public company identity, funding, and legal entity disclosure may reduce trust.

## 6. Founder profile: Henry Langmack

### High-confidence facts

- Henry was a cofounder and CTO of Cal AI.
- He and Zach Yadegari were high-school friends and built the company while still in school.
- Cal AI launched in May 2024 with photo-based calorie and macro estimation.
- TechCrunch reported that Cal AI used OpenAI and Anthropic models, retrieval-augmented generation, and open food/image datasets; different models were used for different food categories.
- In March 2025, the founders reported more than 5 million downloads in eight months, over 30% retention, and more than $2 million revenue in the preceding month. TechCrunch explicitly said it could not independently validate the download/revenue claims, though app-store ratings/download evidence supported substantial traction.
- MyFitnessPal later told TechCrunch that Cal AI exceeded 15 million downloads and $30 million annual revenue in under two years.
- MyFitnessPal acquired Cal AI in a deal that closed in December 2025 and was announced in March 2026. Deal terms were not disclosed.
- The seven-person team plus contractors was retained. The founders' exact retention arrangements were not disclosed.
- Inference.net identifies Henry as “Co-founder, CTO @ Cal AI” and publishes his testimonial that a custom model improved accuracy and affordability and cut request latency by more than 50%. This is a vendor-hosted, self-reported result, but it is specific technical evidence.
- Henry's current LinkedIn profile associates him with Soar.

### Medium-confidence/secondary facts

- A November 2024 profile says Henry and Zach also launched Grind Clock, which reached 20,000 downloads in its first two weeks but did not sustain growth.
- Secondary profiles describe Henry as a self-taught developer with prior fitness-app experience. This is not as strong as the Cal AI/TechCrunch evidence and should not be repeated as a precise claim without asking him.

### What Henry's record suggests

This is inference, not biography:

- He values consumer simplicity over visible technical complexity.
- He has operated model inference at meaningful consumer scale.
- He has seen that distribution, retention, latency, and unit economics matter more than a technically impressive demo.
- He is likely to respond better to shipped proof and sharp product observations than to broad enthusiasm.
- Because Cal AI won by removing manual calorie-entry friction, Soar appears to apply the same product instinct to flight booking: remove repetitive steps and make a complex workflow feel immediate.

### Identity/title caution

Public evidence clearly names Alex Slater as a founder of FlySoar and as the person who publicly launched it. Henry is publicly associated with Soar, but the reviewed sources do not reveal his exact Soar title. This may simply be a young company's incomplete public footprint. In outreach, avoid asserting a title. Ask about the team and role directly on the call.

## 7. Funding analysis

### What is verified

- No public FlySoar/Soar funding announcement, named investor, round size, or valuation was found in the sources reviewed as of 25 June 2026.
- No reliable Crunchbase-style company profile surfaced for this exact flight product.
- Soar's Terms and Privacy pages do not name the operating legal entity.
- The public launch appears very recent: Alex Slater's launch post was captured on 19 May 2026.
- Henry participated in a successful prior company exit, but Cal AI acquisition terms were not disclosed.

### What must not be claimed

- Do not say Soar is bootstrapped as a fact.
- Do not say Henry financed Soar with Cal AI proceeds.
- Do not quote a Cal AI sale price. Public figures such as $50M or $100M are speculation; TechCrunch says terms were undisclosed.
- Do not say FlySoar has raised zero dollars. Absence of a public announcement is not proof of no financing.

### Best working hypothesis

Soar looks like a recently launched, founder-financed or quietly financed company operating before a public institutional round. That is an inference based on its age, founder-led support, and lack of public round data. Confirm with a neutral call question:

> “How are you thinking about the next 12 months: staying lean and revenue-funded, or building the team ahead of a financing milestone?”

## 8. Why Faisal is a credible match

### Corpus reviewed

A fresh aggregate pass over `~/.codex` found:

- 299 parseable session records across active and archived Codex sessions.
- Approximately 5.53 million characters of filtered user-authored task text.
- One malformed JSONL line; all valid records after it were separately recovered.
- The heaviest work directories were Tailorec backend (76 sessions), frontend (46), open-agent (45), openclaw-browser (28), and LinkedIn agent (17).

An earlier Obsidian evidence map independently analyzed 274 Codex chat files and 4,435 user task messages, plus Pi and Qwen histories. The methods and dates differ, so the counts should not be added together. Both analyses point to the same durable work themes.

No raw private transcript, credential, token, or personal configuration should be copied into an application or sent to Henry.

### Strongest fit evidence

#### 1. End-to-end product ownership

Tailorec spans:

- Next.js/React product UI;
- FastAPI/Python domain APIs;
- PostgreSQL/SQLAlchemy/Alembic data;
- recommendation and LLM-assisted workflows;
- an event-persisted TypeScript agent runtime;
- a Playwright browser-control service;
- analytics and AWS infrastructure.

This matches a founding engineer's actual job: move across user experience, backend state, third-party APIs, infrastructure, and debugging without waiting for team boundaries.

#### 2. Async workflow and state-machine experience

Open-agent and the frontend workspace handle long-running runs, streamed events, user approvals, missing fields, cancellation, retries, artifacts, and recovery. Soar has the same class of engineering problem in a different domain: search events, repricing, payment, ticketing, changes, refunds, alerts, and operator intervention.

#### 3. Browser and external-system reliability

Openclaw-browser uses semantic snapshots, stable references, session ownership, Playwright/CDP, remote browser capacity, isolation, readiness, quarantine, and retry behavior. This demonstrates experience making unreliable external web workflows observable and recoverable.

#### 4. Cloud and operations ownership

The local evidence includes AWS/Terraform work across ECS, RDS, S3, ECR, ALB, VPC, IAM, Secrets Manager, CloudWatch, and Lambda. A June 2026 operation safely snapshotted the production database and tore down the full Terraform-managed backend while preserving the Amplify frontend, then verified resource deletion. This is concrete infrastructure ownership, not a cloud keyword list.

#### 5. Production debugging mindset

The Emergent interview simulator work converted real frontend, auth, CORS, container, database-pool, and agent-loop failures into evidence-driven incident exercises. The reusable reasoning pattern is facts → hypotheses → next test → mitigation → customer update. That maps directly to flight booking/support incidents.

#### 6. Integrations and webhook correctness

The Bolna-to-Slack assignment was taken from docs through implementation, reliability hardening, and live ngrok testing. Its hard parts were real payload validation, completion-event filtering, idempotency/duplicate delivery, and recovery. These are relevant to airline/payment webhook orchestration.

#### 7. First-principles engineering range

- uqaabOS: 32-bit monolithic kernel, interrupts, drivers, custom memory allocation, FAT32, terminal, and scheduling.
- Jahan: Python WSGI framework and custom development server.
- jh-vcs: Git-like version-control project in C/C++ (claim from the user's verified application ledger; re-check the public repository before sending a link).

These projects show an ability to work below framework abstractions, useful when debugging networking, concurrency, state, or performance.

#### 8. External contribution evidence

The vault records merged Wagtail contributions for InlinePanel lifecycle events, image-rendition progress, and focus behavior, plus a Hermes Agent path-normalization fix accepted by cherry-pick with authorship preserved. Verify current URLs/status immediately before sharing.

#### 9. High-agency personal story

The user's notes say he began freelancing in high school, earned nearly $5,000 from global clients, helped pay school/college expenses, and once learned Django and GraphQL in roughly two to three days to deliver a client project. These are strong behavioral signals if told plainly and truthfully, without turning them into inflated technical claims.

### The direct mapping to Soar

| Soar need | Faisal evidence |
| --- | --- |
| Live, async product state | SSE/event-driven agent workspace and persisted runtime events |
| External API unreliability | Browser/ATS orchestration, retries, stale refs, webhook work |
| Payment/booking correctness | Integration/state-machine mindset; must still learn travel-specific reconciliation |
| Full-stack velocity | Next.js frontend + FastAPI backend + TypeScript runtimes |
| Infrastructure ownership | AWS/Terraform/ECS/RDS and verified teardown/operations work |
| Sensitive workflows | Scoped tokens, trust boundaries, approval gates, logging/redaction |
| Founder-level ambiguity | Repeated history of converting vague assignments into shipped systems/docs/tests |
| Customer support/debugging | Incident reasoning and customer-update framing |

### Gaps to acknowledge

- No verified direct GDS/NDC/Duffel production experience.
- No verified high-volume consumer travel product experience.
- Stripe/payment experience should be described only to the level actually implemented in Tailorec or assignments; do not imply PCI/payment-orchestration expertise without proof.
- The `10K+ users` and `250K+ requests` Tailorec numbers appear in prior positioning summaries, but the interview portfolio's evidence policy says metrics must be verified against dashboards before public use. Do not send those numbers until re-verified.
- Tailorec ownership may have been collaborative or agent-assisted. Be precise about personally authored decisions and modules.

The right framing is: “I have the adjacent systems experience and can learn the travel domain quickly,” not “I already know flight infrastructure.”

## 9. How to impress Henry

### Lead with one observation

> “The hard part is not rendering flight results. It is making search, fare freshness, payment, ticketing, and post-booking support behave like one transaction even though multiple external systems can change independently.”

This is specific, true, and tied to the product.

### Then connect one proof point

> “I built a product/runtime/browser stack where long-running external workflows had persisted events, retries, approvals, cancellation, and operator-visible traces. Different domain, same reliability problem.”

### Offer a concrete first contribution

Choose one, not all three:

1. **Booking reliability:** define the booking/payment/ticketing state machine, idempotency contract, reconciliation job, and failure dashboard.
2. **Search quality:** instrument supplier latency, reprice rate, offer failure, and post-click booking conversion so “best” reflects reliability, not only fare/duration.
3. **PII/security:** map traveler-document access, encryption, retention, deletion, audit logging, and browser security headers.

Booking reliability is the strongest match to Faisal's evidence and the highest-value founding-engineer conversation.

### Questions worth asking on the call

1. “What breaks most often today: supplier search, repricing, payment, ticketing, or post-booking servicing?”
2. “Is Duffel the primary bookable supply path, and how are you thinking about supplier redundancy?”
3. “What does the booking state machine look like when payment succeeds but ticketing times out?”
4. “Which metric matters most right now: searches, completed bookings, repeat travelers, or support load per booking?”
5. “Where do you want the moat to compound: group travel, post-booking automation, ranking data, or distribution?”
6. “What would you expect a founding engineer to own in the first four weeks?”
7. “How are you thinking about financing and hiring over the next 12 months?”

Do not ask all seven. Pick three based on the conversation.

### A credible 30-day proposal

- Week 1: ship one user-visible bug/flow improvement; map search-to-ticketing states and production telemetry.
- Week 2: add or tighten failure classification, idempotency, and reconciliation around one booking path.
- Week 3: build an operator view for stuck/failed bookings and support handoff.
- Week 4: use failure and conversion data to improve ranking or supplier routing; document the next reliability/security priorities.

## 10. WhatsApp situation and next message

### What happened

- On Sunday, 21 June, Henry corrected his name after Faisal addressed him as Nathan.
- Faisal apologized and expressed interest in learning more.
- Henry asked at 9:44 pm IST whether Faisal was free later that day.
- Faisal replied 38 minutes later, declined that day, and proposed 5:30 pm GMT the next day.
- Henry did not reply.
- It is now Wednesday evening in US Eastern Time / early Thursday in India. A concise follow-up now is reasonable.

The problem was not a fatal rejection. The scheduling message required Henry to recover an expired time, and the earlier name mistake weakened momentum. The next message should reduce friction, show one real insight, and make the call easy to schedule.

### Recommended message to send now

> Hey Henry — following up because I’m genuinely interested in what you’re building at Soar. I spent time understanding the product, and the problem that stood out to me is making search, repricing, payment, ticketing, and post-booking support feel like one reliable flow even when the underlying providers fail independently. I’ve built similar event-driven agent/browser systems with retries, approvals, and production tracing, so I think I could contribute meaningfully. If you’re still open to chatting, send me any 20-minute window that works for you this week and I’ll make it work.

### Shorter version

> Hey Henry — wanted to follow up because I’m genuinely interested in Soar. The hard problem I see isn’t just flight search; it’s making repricing, payment, ticketing, and post-booking support feel like one reliable flow. I’ve built similar event-driven systems with retries and production tracing and think I could contribute. If you’re still open to chatting, send me any 20-minute window this week and I’ll make it work.

### Why this version is better

- It does not repeat a long apology.
- It avoids the Emergent AI interview, which would sound like leverage or divided attention.
- It does not claim private/internal knowledge.
- It shows product understanding in one sentence.
- It connects that observation to defensible experience.
- It removes timezone negotiation: Henry can choose any window.

### What not to send

- Do not mention that you inspected client bundles or API routes.
- Do not send the full dossier.
- Do not pitch three projects, your life story, or every technology.
- Do not say Soar is funded/unfunded.
- Do not call Henry the sole founder or CTO of Soar.
- Do not mention Emergent unless he asks about your timeline or other interviews.
- Do not apologize repeatedly or say you “didn't want to waste his time”; that makes the conversation heavier.

### Follow-up cadence

Send the recommended message now. If there is no answer, wait until Monday, 29 June, then send one final line:

> Last follow-up from me — I’d still love to talk about contributing to Soar. If timing isn’t right, no problem; I’ll keep following what you build.

After that, stop messaging unless there is a real new artifact or he responds.

## 11. Interview positioning in 30 seconds

> I’m a full-stack/product engineer who tends to own the messy boundaries. On Tailorec I worked across the Next.js product, FastAPI backend, AWS infrastructure, an event-persisted agent runtime, and a Playwright browser service. The hardest part was not getting an agent to click; it was making long-running external workflows observable, recoverable, and interruptible by the user. Soar has a similar systems problem across live search, changing fares, payment, ticketing, and support. I do not have travel-domain experience yet, but I can bring that reliability and ownership mindset and learn the supplier domain quickly.

## 12. Sources

### Soar primary/public product sources

- [Soar live product](https://flysoar.ai/)
- [Soar Privacy Policy](https://flysoar.ai/privacy)
- [Soar Terms & Conditions](https://flysoar.ai/terms)
- [Soar web manifest](https://flysoar.ai/manifest.webmanifest)
- [Soar sitemap](https://flysoar.ai/sitemap.xml)

### Founder and Cal AI sources

- [TechCrunch: Cal AI built by two teenagers (16 March 2025)](https://techcrunch.com/2025/03/16/photo-calorie-app-cal-ai-downloaded-over-a-million-times-was-built-by-two-teenagers/)
- [TechCrunch: MyFitnessPal acquired Cal AI (2 March 2026)](https://techcrunch.com/2026/03/02/myfitnesspal-has-acquired-cal-ai-the-viral-calorie-app-built-by-teens/)
- [Inference.net Henry Langmack testimonial/profile](https://inference.net/explore)
- [Henry Langmack LinkedIn](https://www.linkedin.com/in/henrylangmack)
- [Captured Alex Slater FlySoar launch post](https://bittide.aicompass.dev/article/35173d4c-d012-4849-b82e-3c3928ca8e58)
- [Secondary report mentioning Grind Clock](https://cdn.businessday.ng/wp-content/uploads/2024/11/BD_20241109.pdf)

### Competitor primary sources

- [Google Flights: track flights and prices](https://support.google.com/travel/answer/6235879?hl=en)
- [Google Flights: finding best fares](https://support.google.com/travel/answer/7664728?hl=en)
- [Skyscanner: prices, flexible search, Everywhere, and alerts](https://help.skyscanner.net/hc/en-us/sections/200350582-Prices-on-Skyscanner)
- [KAYAK Flights](https://www.kayak.com/flights)
- [Hopper price predictions](https://help.hopper.com/en_us/about-our-price-predictions-Hy7cLt_Fv)
- [Hopper flight booking](https://help.hopper.com/en_us/how-to-book-a-flight-Hka98Yutw)

### Local evidence consulted

- `/home/faishal/.codex/sessions/` and `/home/faishal/.codex/archived_sessions/` (aggregate analysis only)
- `/home/faishal/.codex/memories/rollout_summaries/`
- `/home/faishal/.codex/life/projects/interview-portfolio/`
- `/home/faishal/Documents/Obsidian Vault/01 Projects/Interview Portfolio/`
- `/home/faishal/Documents/Obsidian Vault/Applications/YC  APPLICATION.md`
- Supplied WhatsApp transcript: `/home/faishal/.codex/attachments/dfce0626-9d61-4917-81e8-2d47f0a25fcb/pasted-text-1.txt`

## Final recommendation

Send the shorter WhatsApp message now. If Henry responds, do not open with a résumé dump. Open with the booking-correctness observation, ask what currently breaks, then connect his answer to one concrete Tailorec reliability story. The objective of the first call is not to prove you know everything about flights. It is to make Henry believe you can take ownership of an ugly production problem next week and close the loop without supervision.
