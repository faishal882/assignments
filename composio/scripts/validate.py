#!/usr/bin/env python3
"""Validate the public dataset and its audit trail as one consistency boundary."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "id", "name", "category", "description", "auth", "access", "api",
    "mcp", "verdict", "blocker", "evidence", "confidence", "checkedAt",
}
ACCESS = {"Self-serve", "Plan/admin", "Open source", "Review required", "Contact sales"}
VERDICTS = {"Build now", "Build with constraints", "Outreach first", "No public API"}
CONFIDENCE = {"High", "Medium", "Low"}


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> int:
    rows = load("data/apps.json")
    seed = load("data/apps-seed.json")
    verification = load("data/verification.json")
    identities = load("data/app-identities.json")
    patterns = load("data/patterns.json")
    errors: list[str] = []

    expected_names = [name for group in seed for name in group["apps"]]
    expected_categories = [group["category"] for group in seed]
    if len(rows) != 100:
        errors.append(f"expected 100 rows, found {len(rows)}")
    if [row.get("id") for row in rows] != list(range(1, 101)):
        errors.append("ids must be ordered integers 1..100")
    if [row.get("name") for row in rows] != expected_names:
        errors.append("dataset names/order differ from apps-seed.json")
    if len(set(expected_categories)) != 10:
        errors.append("seed must contain 10 unique categories")
    if [row.get("app") for row in identities] != expected_names:
        errors.append("identity registry names/order differ from apps-seed.json")
    if any(row.get("source") != "assignment_brief" for row in identities):
        errors.append("every identity must be sourced from the assignment brief")
    if any(not row.get("hosts") for row in identities):
        errors.append("every identity must have at least one official host")
    if "curation" in json.dumps(identities).lower():
        errors.append("identity registry must not depend on curation output")

    for row in rows:
        label = f"{row.get('id', '?')}:{row.get('name', '?')}"
        missing = REQUIRED - row.keys()
        if missing:
            errors.append(f"{label}: missing {', '.join(sorted(missing))}")
        if not isinstance(row.get("auth"), list) or not row.get("auth"):
            errors.append(f"{label}: auth must be a non-empty list")
        if row.get("access") not in ACCESS:
            errors.append(f"{label}: unsupported access {row.get('access')!r}")
        if row.get("verdict") not in VERDICTS:
            errors.append(f"{label}: unsupported verdict {row.get('verdict')!r}")
        if row.get("confidence") not in CONFIDENCE:
            errors.append(f"{label}: unsupported confidence {row.get('confidence')!r}")
        if not str(row.get("description", "")).strip() or not str(row.get("blocker", "")).strip():
            errors.append(f"{label}: description and blocker must be explicit")
        if re.search(r"^(none|n/a)$", str(row.get("blocker", "")).strip(), re.I):
            errors.append(f"{label}: blocker cannot be a placeholder")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{label}: evidence must be a non-empty list")
        for item in evidence if isinstance(evidence, list) else []:
            url = str(item.get("url", "")) if isinstance(item, dict) else ""
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                errors.append(f"{label}: invalid HTTPS evidence URL {url!r}")
        try:
            date.fromisoformat(str(row.get("checkedAt")))
        except ValueError:
            errors.append(f"{label}: checkedAt must be an ISO date")

    categories = Counter(row.get("category") for row in rows)
    if categories != Counter({category: 10 for category in expected_categories}):
        errors.append(f"expected 10 apps in each category, found {dict(categories)}")
    if len({row.get("name") for row in rows}) != len(rows):
        errors.append("duplicate app names")

    method = verification.get("method", {})
    samples = verification.get("samples", [])
    claims = verification.get("claimAudit", [])
    if method.get("sampleSize") != len(samples) or len(samples) != 20:
        errors.append("verification sampleSize must match 20 sample rows")
    if len({sample.get("id") for sample in samples}) != len(samples):
        errors.append("verification sample ids must be unique")
    if any(sample.get("id") not in range(1, 101) for sample in samples):
        errors.append("verification sample id outside dataset")
    if len(claims) != 160:
        errors.append(f"verification must contain 160 field-level claims, found {len(claims)}")
    claim_keys = {(claim.get("appId"), claim.get("field")) for claim in claims}
    if len(claim_keys) != len(claims):
        errors.append("verification claim app/field keys must be unique")
    expected_claim_keys = {
        (sample["id"], field)
        for sample in samples
        for field in method.get("claimFields", [])
    }
    if claim_keys != expected_claim_keys:
        errors.append("verification ledger does not cover every sample field exactly once")
    for phase in ("firstPass", "finalPass"):
        score = method.get(phase, {})
        supported, total, accuracy = score.get("supportedClaims"), score.get("totalClaims"), score.get("accuracy")
        if not isinstance(supported, int) or not isinstance(total, int) or not total:
            errors.append(f"verification {phase} totals are invalid")
        elif round(100 * supported / total, 1) != accuracy:
            errors.append(f"verification {phase} accuracy does not match its totals")
        claim_key = "firstSupported" if phase == "firstPass" else "finalSupported"
        computed = sum(bool(claim.get(claim_key)) for claim in claims)
        if supported != computed:
            errors.append(f"verification {phase} declares {supported}, but claim ledger sums to {computed}")
    for sample in samples:
        sample_claims = [claim for claim in claims if claim.get("appId") == sample.get("id")]
        if sample.get("first") != sum(bool(claim.get("firstSupported")) for claim in sample_claims):
            errors.append(f"verification sample {sample.get('id')} first score differs from its claims")
        if sample.get("final") != sum(bool(claim.get("finalSupported")) for claim in sample_claims):
            errors.append(f"verification sample {sample.get('id')} final score differs from its claims")
        if not sample.get("sourceUrls"):
            errors.append(f"verification sample {sample.get('id')} has no source URL")
    if any(not claim.get("sources") or not claim.get("verificationMethods") for claim in claims):
        errors.append("every verification claim needs sources and verification methods")

    document_review_path = ROOT / "artifacts/document-review.json"
    if not document_review_path.exists():
        errors.append("document review artifact is missing")
    else:
        document_review = json.loads(document_review_path.read_text(encoding="utf-8"))
        reviewed = document_review.get("reviews", [])
        if {row.get("appId") for row in reviewed} != {sample.get("id") for sample in samples}:
            errors.append("document review must cover the same 20 sampled apps")
        if document_review.get("summary", {}).get("reviewedClaims") != len(claims):
            errors.append("document review claim total differs from the verification ledger")
        review_unsupported = {
            (row.get("appId"), field)
            for row in reviewed
            for field in row.get("unsupportedFields", [])
        }
        ledger_unsupported = {
            (claim.get("appId"), claim.get("field"))
            for claim in claims
            if not claim.get("finalSupported")
        }
        if review_unsupported != ledger_unsupported:
            errors.append("document review unsupported fields differ from the verification ledger")
        if any(not row.get("sources") or not row.get("note") for row in reviewed):
            errors.append("every document review row needs sources and a reviewer note")

    if patterns.get("total") != len(rows):
        errors.append("patterns total differs from dataset")
    expected_access = Counter(row["access"] for row in rows)
    expected_verdicts = Counter(row["verdict"] for row in rows)
    if Counter(patterns.get("access", {})) != expected_access:
        errors.append("patterns access counts differ from dataset")
    if Counter(patterns.get("verdicts", {})) != expected_verdicts:
        errors.append("patterns verdict counts differ from dataset")
    review_ids = {row["id"] for row in rows if row["access"] == "Review required"}
    outreach_ids = {row["id"] for row in rows if row["verdict"] == "Outreach first"}
    expected_gate = {
        "formalReview": len(review_ids),
        "outreachFirst": len(outreach_ids),
        "overlap": len(review_ids & outreach_ids),
        "uniqueApps": len(review_ids | outreach_ids),
    }
    if patterns.get("humanGate") != expected_gate:
        errors.append("patterns human-gate union/overlap is inconsistent")

    latest_path = ROOT / "artifacts/research.latest.json"
    if latest_path.exists():
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
        agent_rows = latest.get("rows", [])
        if [row.get("id") for row in agent_rows] != list(range(1, 101)):
            errors.append("latest agent artifact must contain ordered IDs 1..100")
        if latest.get("completed") != len(agent_rows):
            errors.append("latest agent completed count differs from row count")
        if latest.get("researched") != sum(row.get("status") == "researched" for row in agent_rows):
            errors.append("latest agent researched count is inconsistent")
        if latest.get("needsHumanReview") != sum(row.get("status") == "needs_human_review" for row in agent_rows):
            errors.append("latest agent review count is inconsistent")
        for row in agent_rows:
            if row.get("status") == "researched":
                primary = row.get("primaryEvidence") or {}
                if not primary.get("official") or not primary.get("technical"):
                    errors.append(f"agent row {row.get('id')}: auto-cleared without official technical evidence")

        manifest_path = ROOT / "artifacts/curation-manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            held_ids = {row.get("id") for row in agent_rows if row.get("status") == "needs_human_review"}
            manifest_ids = {row.get("id") for row in manifest.get("reviewQueue", [])}
            if manifest_ids != held_ids:
                errors.append("curation manifest must contain every agent-held app exactly once")
            if manifest.get("humanReviewCount") != len(held_ids):
                errors.append("curation manifest review count is inconsistent")
            if manifest.get("autoCleared") != len(agent_rows) - len(held_ids):
                errors.append("curation manifest auto-cleared count is inconsistent")

    browser_path = ROOT / "artifacts/browser-verification.json"
    if browser_path.exists():
        browser = json.loads(browser_path.read_text(encoding="utf-8"))
        browser_rows = browser.get("results", [])
        sample_ids = {sample.get("id") for sample in samples}
        if {row.get("appId") for row in browser_rows} != sample_ids:
            errors.append("browser verification must cover the same 20 sampled apps")
        if browser.get("summary", {}).get("total") != len(browser_rows):
            errors.append("browser verification total differs from its result count")
        if browser.get("summary", {}).get("loaded") != sum(bool(row.get("loaded")) for row in browser_rows):
            errors.append("browser verification loaded count is inconsistent")

    if errors:
        print("\n".join(errors))
        return 1

    summary = {
        "rows": len(rows),
        "categories": len(categories),
        "verdicts": dict(sorted(Counter(row["verdict"] for row in rows).items())),
        "access": dict(sorted(Counter(row["access"] for row in rows).items())),
        "confidence": dict(sorted(Counter(row["confidence"] for row in rows).items())),
        "verificationSamples": len(samples),
        "verificationClaims": len(claims),
        "verificationFirst": method.get("firstPass", {}).get("accuracy"),
        "verificationFinal": method.get("finalPass", {}).get("accuracy"),
        "uniqueHumanGates": patterns.get("humanGate", {}).get("uniqueApps"),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
