# Toolkit Radar

An evidence-backed build-versus-outreach map for 100 app integrations. This repository is the source for a two-minute case study and the reproducible research agent behind it.

**[View the live case study](https://faishal882.github.io/composio-toolkit-radar/)**

## What is here

- `index.html` — the single-page case study and interactive 100-app matrix.
- `data/apps.json` — the reviewed, machine-readable final dataset.
- `data/app-identities.json` — entity locks generated only from websites in the supplied brief.
- `data/patterns.json` — generated auth, access, blocker, category, and buildability clusters.
- `data/verification.json` — the recomputable 20-app, 160-claim verification ledger.
- `agent/research.py` — the resumable Composio-powered discovery agent.
- `artifacts/research.raw.json` — immutable first-pass answers and citations for all 100 apps.
- `artifacts/research.latest.json` — output from the stronger Python agent, with evidence scores and a review queue.
- `artifacts/curation-manifest.json` — the exact apps held for independent review and their final decisions.
- `artifacts/document-review.json` — the completed 20-app document review, sources, corrections, and bounded uncertainty.
- `data/curation.json` — the explicit reviewer decisions that fix collisions and unsupported claims.
- `scripts/curate.py` — materializes reviewed decisions while keeping the raw artifact immutable.
- `scripts/validate.py` — schema, taxonomy, audit-math, URL, and cross-file consistency gates.
- `scripts/check_evidence.py` — concurrent reachability checks for every primary evidence URL.
- `scripts/browser_verify.py` — Chromium-backed verification of the 20 sampled source pages.
- `tests/test_research_agent.py` — regression tests for identity collisions and CLI envelopes.

## Run the case study

Requirements: Python 3.10+ for the zero-dependency local server and pipeline.

```bash
npm run serve
```

Open <http://localhost:4173>.

## Run the research agent

Requirements:

1. Install the current [Composio CLI](https://docs.composio.dev/docs/cli).
2. Authenticate with `composio login`.
3. Confirm the `composio_search` toolkit is connected with `composio whoami` and `composio search "fetch a public webpage"`.

Run the full set:

```bash
npm run research -- --limit 100 --concurrency 4
```

Run a cheap smoke test without overwriting the included raw artifact:

```bash
npm run research -- --limit 3 --output artifacts/live/smoke.json
```

The Python agent calls the signed-in Composio CLI's `COMPOSIO_SEARCH_WEB` tool. It locks each app to provider domains extracted from the assignment brief, scores citations, retries transient failures with backoff, writes an atomic checkpoint after every completed app, and sends weak or mismatched results to `needs_human_review`. It never reads the final curation file to determine identity. No Composio API key is copied into this repository.

The included clean run completed 100/100 requests with no request failures. It auto-cleared 58 apps with official technical evidence and held 42 for review. This is deliberately conservative: an official vendor blog can establish identity, but only provider technical documentation can auto-clear API and authentication claims.

Resume an interrupted run without repeating completed IDs:

```bash
npm run research -- --limit 100 --resume
```

## Research and verification loop

```text
100 exact entities
      ↓
Python orchestration + Composio discovery
      ↓
identity locks + scored citations + checkpoints
      ↓
explicit reviewer queue
      ↓
immutable curation decisions + 100-row gates
      ↓
20-app claim-level audit
```

The first pass scored **101/160 supported claims (63.1%)** on the verification set. After document-by-document review, it scored **157/160 (98.1%)**. The final three unsupported claim-points remain visible rather than being guessed.

Because ten of the twenty apps were deliberately adversarial, this is a verification-set support rate, not a population-wide accuracy estimate. The cohorts are reported separately: category-stratified **79/80 → 80/80**, and adversarial **22/80 → 77/80**. Every total is generated from the 160 field-level records in `data/verification.json` and cross-checked against `artifacts/document-review.json`.

The most important failure classes were:

- **Name collisions:** Sherlock resolved to an unrelated payment product.
- **Entity drift:** Mermaid CLI became the separate Mermaid Chart SaaS.
- **Vendor confusion:** Paygent Connect became an unrelated AI-billing product; iPayX became IXOPAY.
- **Citation contamination:** Close and Plain received unrelated MCP sources.
- **Official/community confusion:** a community adapter was initially treated as first-party MCP.

## Validate the final artifact

```bash
npm run validate
npm test
npm run check:evidence
npm run verify:browser
```

`validate` fails on missing rows/fields, identity leakage, order or taxonomy drift, duplicate IDs or names, invalid URLs or enum values, claim-ledger arithmetic inconsistencies, empty evidence, or overlapping gate counts reported as unique. Unit tests protect the collision guards, Composio response parser, and generated metrics. `check:evidence` checks all 100 links; `verify:browser` uses persistent Chromium for the 20-app audit set.

Regenerate every deterministic artifact:

```bash
npm run build:data
```

The 20 sampled apps have already been independently reviewed source-by-source; the record is in `artifacts/document-review.json`. It is deliberately disclosed as an AI-assisted manual source review, not falsely described as human signoff. A human or vendor contact is still genuinely required to inspect Fanbasis details hidden behind its authenticated developer portal.

Some documentation providers return 403/429 to automated clients while loading in a browser. Those cases are retained in the evidence report instead of being silently counted as healthy.

## Dataset fields

Each app records:

- category and one-line product description;
- authentication methods;
- credential path (`Self-serve`, `Plan/admin`, `Review required`, `Contact sales`, or `Open source`);
- API surface and MCP status;
- buildability verdict and the concrete blocker;
- primary evidence URL, confidence, and check date.

## Deliberate limitations

- “None found” means no first-party MCP was located in this research pass, not proof that no community implementation exists.
- Pricing and access rules change quickly; `checkedAt` is present on every row for refresh scheduling.
- No paid vendor accounts were used. A plan or partnership gate is reported as a finding, not bypassed.
- The raw agent is a discovery layer, not an authority. Final claims require provider-owned evidence or remain uncertain.
