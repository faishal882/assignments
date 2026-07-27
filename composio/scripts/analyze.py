#!/usr/bin/env python3
"""Generate all portfolio findings from the reviewed 100-app dataset."""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/apps.json"
OUTPUT = ROOT / "data/patterns.json"


def auth_family(row: dict, terms: tuple[str, ...]) -> bool:
    values = " ".join(row["auth"]).lower()
    return any(term in values for term in terms)


def blocker_type(row: dict) -> str:
    blocker = row["blocker"].lower()
    if row["verdict"] == "No public API":
        return "No public API"
    if row["access"] == "Contact sales":
        return "Partnership / sales gate"
    if row["access"] == "Review required":
        return "Formal app review"
    if row["access"] == "Plan/admin":
        return "Paid plan / admin"
    if any(term in blocker for term in ("rate limit", "quota", "credit", "usage", "polling")):
        return "Rate limits / usage"
    if any(term in blocker for term in ("version", "schema", "plugins", "deployments", "differ")):
        return "Version / schema variance"
    if any(term in blocker for term in ("regulatory", "country", "compliance", "sensitive", "money movement")):
        return "Compliance / safety"
    if any(term in blocker for term in ("review", "approval", "approved", "marketplace", "partner")):
        return "Distribution review"
    if any(term in blocker for term in ("admin", "permission", "scope", "role", "shared")):
        return "Permissions / tenant setup"
    if row["access"] == "Open source":
        return "Local hosting / execution"
    return "Integration design"


def atomic_write(payload: object) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, OUTPUT)


def main() -> None:
    rows = json.loads(INPUT.read_text(encoding="utf-8"))
    access = Counter(row["access"] for row in rows)
    verdicts = Counter(row["verdict"] for row in rows)
    mcp = Counter(row["mcp"] for row in rows)
    blockers = Counter(blocker_type(row) for row in rows)
    auth = {
        "OAuth path": sum(auth_family(row, ("oauth",)) for row in rows),
        "API key or token": sum(auth_family(row, ("api key", "api token", "bearer", "access token", "pat", "personal token")) for row in rows),
        "Basic credentials": sum(auth_family(row, ("basic",)) for row in rows),
        "No authentication": sum(auth_family(row, ("no auth",)) for row in rows),
        "Unknown": sum(auth_family(row, ("unknown",)) for row in rows),
    }
    categories = []
    for category in dict.fromkeys(row["category"] for row in rows):
        members = [row for row in rows if row["category"] == category]
        category_access = Counter(row["access"] for row in members)
        category_verdicts = Counter(row["verdict"] for row in members)
        categories.append(
            {
                "category": category,
                "total": len(members),
                "selfServeOrOpen": category_access["Self-serve"] + category_access["Open source"],
                "gated": len(members) - category_access["Self-serve"] - category_access["Open source"],
                "buildNow": category_verdicts["Build now"],
                "outreachOrHold": category_verdicts["Outreach first"] + category_verdicts["No public API"],
            }
        )
    review_ids = {row["id"] for row in rows if row["access"] == "Review required"}
    outreach_ids = {row["id"] for row in rows if row["verdict"] == "Outreach first"}
    payload = {
        "generatedFrom": "data/apps.json",
        "total": len(rows),
        "authNonExclusive": auth,
        "access": dict(access),
        "verdicts": dict(verdicts),
        "mcp": dict(mcp),
        "officialMcpIncludingBeta": mcp["Official"] + mcp["Official beta"],
        "blockers": dict(blockers.most_common()),
        "topBlocker": {"type": blockers.most_common(1)[0][0], "count": blockers.most_common(1)[0][1]},
        "categories": categories,
        "humanGate": {
            "formalReview": len(review_ids),
            "outreachFirst": len(outreach_ids),
            "overlap": len(review_ids & outreach_ids),
            "uniqueApps": len(review_ids | outreach_ids),
        },
    }
    atomic_write(payload)
    print(json.dumps({"output": str(OUTPUT.relative_to(ROOT)), "topBlocker": payload["topBlocker"], "humanGate": payload["humanGate"]}, indent=2))


if __name__ == "__main__":
    main()
