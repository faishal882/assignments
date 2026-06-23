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
- Session initialized with empty dossier. Next: gather public website/social/company data, then local fit signals.
