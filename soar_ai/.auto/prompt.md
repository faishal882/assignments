# Autoresearch: Flysoar founder-fit research dossier

## Objective
Build a credible, evidence-backed dossier for impressing FlySoar / Soar AI founder Henry Langmack and positioning Faishal for a founding engineer role. Research: flysoar.ai product, internal/technical workings from public signals, competitor landscape, founder background/achievements, funding, and fit analysis from local Codex conversations + Obsidian vault.

## Metrics
- **Primary**: evidence_items (count, higher is better) — number of evidence-backed bullets/citations captured in `research/flysoar_dossier.md`.
- **Secondary**: source_urls, sections_complete, local_fit_signals — breadth and personalization monitors.

## How to Run
`./.auto/measure.sh` — outputs `METRIC name=value` lines.

## Files in Scope
- `research/flysoar_dossier.md` — final research dossier and outreach strategy.
- `research/sources.md` — source list, raw extracted notes, caveats.
- `.auto/ideas.md` — deferred research leads.
- `.auto/measure.sh` — measurement script for research completeness.

## Off Limits
- Do not modify user files under `~/.codex/` or the Obsidian vault.
- Do not invent facts. Mark unverified claims clearly.
- Do not scrape private/authenticated data or bypass access controls.

## Constraints
- Use public sources and local user-owned notes only.
- Cite URLs or local file paths for every specific claim.
- Respect privacy: summarize local conversations/notes without exposing sensitive secrets.
- No benchmark cheating: improve evidence quality and breadth, not just counts.

## What's Been Tried
- Built and kept the baseline measurement script.
- Gathered public product/legal/X/client-bundle evidence for Soar: Next.js frontend, Duffel booking provider, Stripe-like billing, Twilio/passkeys, analytics, shareable deal URLs, booking/hold/progress/result routes.
- Gathered Henry Langmack public X signals: Soar link, “18. Making fun products,” internal-tools bias, Cal AI/app-studio hiring/growth signals, app charting, offline sync, paywall experimentation, SwiftUI hiring.
- Added local fit signals from Obsidian/Codex: Tailorec full-stack/agent/runtime/analytics/AWS experience, OS-from-scratch achievement, MVP narrowing and debugging orientation.
- Added competitor positioning, 30/60/90 plan, quick cheat sheet, outreach draft, five-minute call script, follow-up teardown/prototype plan, first-contact variants, standalone teardown, objection handling, and 48-hour work-trial plan.
- Next promising directions: polish artifacts for final delivery, add a one-page resume/portfolio positioning section, or improve source coverage if new public company/funding data appears; avoid adding low-quality bullets just for counts.
