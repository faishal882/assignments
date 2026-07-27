#!/usr/bin/env python3
"""Build a recomputable 160-claim audit ledger for the 20-app verification set."""

from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/verification.json"
FIELDS = ["identity", "category", "description", "auth", "access", "api", "mcp", "verdict"]

SAMPLES = [
    (4, "stratified", "Attio auth, REST surface, webhooks, and official MCP were directly documented."),
    (12, "stratified", "Intercom's private-token, public OAuth, REST, and remote MCP paths matched docs."),
    (21, "stratified", "Slack's API result was sound; review added the official MCP and admin-install constraint."),
    (31, "stratified", "Google Ads requires OAuth plus a developer token and reviewed production access."),
    (43, "stratified", "BigCommerce documents REST, GraphQL, OAuth tokens, dev stores, and hosted MCP."),
    (53, "stratified", "Ahrefs key/OAuth paths and plan-gated production access were supported."),
    (61, "stratified", "GitHub REST, GraphQL, token types, and official MCP were directly supported."),
    (71, "stratified", "Notion internal tokens, public OAuth, REST, and hosted MCP matched docs."),
    (81, "stratified", "Stripe API keys, Connect OAuth, REST, and hosted MCP matched docs."),
    (92, "stratified", "Otter's Enterprise REST API and OAuth-authenticated MCP were verified in its Help Center."),
    (8, "adversarial", "Close retrieved unrelated vendors. Entity locking replaced the result with Close-owned docs."),
    (17, "adversarial", "Plain retrieved unrelated MCP vendors. Provider-domain enforcement recovered the correct product."),
    (37, "adversarial", "systeme.io auth/API were right, but a community MCP was initially labeled first-party."),
    (50, "adversarial", "Fanbasis relied on unofficial packages. Official docs are login-gated, so access remains uncertain."),
    (58, "adversarial", "Sherlock resolved to a payment product instead of the supplied open-source username CLI."),
    (84, "adversarial", "Paygent Connect resolved to an unrelated AI-billing product; public API breadth remains uncertain."),
    (85, "adversarial", "iPayX was conflated with IXOPAY. No public developer docs were located for auth or API."),
    (91, "adversarial", "The first pass checked consumer NotebookLM; review found the licensed Enterprise preview API."),
    (98, "adversarial", "Mermaid CLI drifted to Mermaid Chart. The target is the supplied local open-source CLI."),
    (99, "adversarial", "The first pass researched another transcript vendor; domain locking recovered transcriptapi.com."),
]

ALL = set(FIELDS)
FIRST_SUPPORTED = {
    4: ALL, 12: ALL, 21: ALL - {"mcp"}, 31: ALL, 43: ALL, 53: ALL, 61: ALL, 71: ALL, 81: ALL, 92: ALL,
    8: {"category"}, 17: {"category"},
    37: {"identity", "category", "description", "auth", "api", "verdict"},
    50: {"identity", "category", "description"}, 58: {"category"}, 84: {"category"}, 85: {"category"},
    91: {"identity", "category", "description"}, 98: {"category", "description"},
    99: {"category", "description", "api"},
}


def value_for(row: dict, field: str):
    if field == "identity":
        return row["name"]
    value = row[field]
    return "; ".join(value) if isinstance(value, list) else value


def atomic_write(payload: object) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, OUTPUT)


def main() -> None:
    apps = json.loads((ROOT / "data/apps.json").read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in apps}
    document_review = json.loads((ROOT / "artifacts/document-review.json").read_text(encoding="utf-8"))
    reviews = {row["appId"]: row for row in document_review["reviews"]}
    claims = []
    sample_rows = []
    for app_id, cohort, note in SAMPLES:
        row = by_id[app_id]
        review = reviews[app_id]
        source_urls = review["sources"]
        first_supported = FIRST_SUPPORTED[app_id]
        final_unsupported = set(review["unsupportedFields"])
        for field in FIELDS:
            claims.append(
                {
                    "appId": app_id,
                    "app": row["name"],
                    "cohort": cohort,
                    "field": field,
                    "firstSupported": field in first_supported,
                    "finalSupported": field not in final_unsupported,
                    "finalValue": value_for(row, field),
                    "sources": source_urls,
                    "firstPassArtifact": {"path": "artifacts/research.raw.json", "rowId": app_id},
                    "verificationMethods": ["assignment identity lock", "provider document review", "Chromium browser check"],
                    "checkedAt": row["checkedAt"],
                    "note": review["note"] if field not in first_supported or field in final_unsupported else "Supported under the documented field policy in artifacts/document-review.json.",
                }
            )
        sample_rows.append(
            {
                "id": app_id,
                "app": row["name"],
                "cohort": cohort,
                "first": len(first_supported),
                "final": len(FIELDS) - len(final_unsupported),
                "result": "hit" if len(first_supported) == len(FIELDS) else ("uncertain" if final_unsupported else "corrected"),
                "note": note,
                "sourceUrls": source_urls,
                "firstPassArtifact": {"path": "artifacts/research.raw.json", "rowId": app_id},
            }
        )

    first_total = sum(claim["firstSupported"] for claim in claims)
    final_total = sum(claim["finalSupported"] for claim in claims)
    cohort_scores = defaultdict(lambda: {"first": 0, "final": 0, "total": 0})
    for claim in claims:
        score = cohort_scores[claim["cohort"]]
        score["first"] += int(claim["firstSupported"])
        score["final"] += int(claim["finalSupported"])
        score["total"] += 1
    cohorts = {
        name: {
            **score,
            "firstAccuracy": round(100 * score["first"] / score["total"], 1),
            "finalAccuracy": round(100 * score["final"] / score["total"], 1),
        }
        for name, score in cohort_scores.items()
    }
    payload = {
        "method": {
            "sampleSize": len(SAMPLES),
            "claimFieldsPerApp": len(FIELDS),
            "claimFields": FIELDS,
            "cohorts": {
                "stratified": "One app per category, selected before manual review.",
                "adversarial": "Ten low-signal, collision-prone, gated, or contradictory results flagged from the raw run.",
            },
            "scoring": "Identity/category score from the locked brief plus provider confirmation; positive technical claims require provider-owned evidence, while 'none found' records a bounded public-source search; verdict scores only when it follows from verified facts or explicit uncertainty. Unknown claims score zero.",
            "scoreLabel": "Verification-set support rate; the adversarial half means this is not a population-wide accuracy estimate.",
            "firstPass": {"supportedClaims": first_total, "totalClaims": len(claims), "accuracy": round(100 * first_total / len(claims), 1)},
            "finalPass": {"supportedClaims": final_total, "totalClaims": len(claims), "accuracy": round(100 * final_total / len(claims), 1)},
            "cohortScores": cohorts,
            "remainingUncertainty": "Three claims remain intentionally unsupported: Fanbasis authentication, access route, and API shape are hidden behind its provider login gate.",
            "independentReview": "All 20 sampled rows were read document-by-document by Codex and recorded in artifacts/document-review.json. This is disclosed as AI-assisted manual review, not human signoff.",
        },
        "samples": sample_rows,
        "claimAudit": claims,
    }
    atomic_write(payload)
    print(json.dumps({"claims": len(claims), "first": payload["method"]["firstPass"], "final": payload["method"]["finalPass"], "cohorts": cohorts}, indent=2))


if __name__ == "__main__":
    main()
