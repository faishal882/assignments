#!/usr/bin/env python3
"""Materialize reviewer decisions without mutating the raw agent artifact."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "artifacts/research.latest.json"
CURATION_PATH = ROOT / "data/curation.json"
OUTPUT_PATH = ROOT / "data/apps.json"
MANIFEST_PATH = ROOT / "artifacts/curation-manifest.json"


def atomic_write(path: Path, payload: object) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> None:
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    reviewed = json.loads(CURATION_PATH.read_text(encoding="utf-8"))
    raw_rows = raw.get("rows", [])
    if len(raw_rows) != 100 or len(reviewed) != 100:
        raise ValueError(f"Expected 100 latest-agent and reviewed rows, got {len(raw_rows)} and {len(reviewed)}")

    for index, (source, decision) in enumerate(zip(raw_rows, reviewed, strict=True), start=1):
        if source.get("app") != decision.get("name"):
            raise ValueError(
                f"Row {index} identity mismatch: raw={source.get('app')!r}, curated={decision.get('name')!r}"
            )
        if source.get("category") != decision.get("category"):
            raise ValueError(f"Row {index} category mismatch for {decision.get('name')}")
        if decision.get("id") != index:
            raise ValueError(f"Row {index} has curated id {decision.get('id')}")

    atomic_write(OUTPUT_PATH, reviewed)
    review_queue = []
    for source, decision in zip(raw_rows, reviewed, strict=True):
        if source.get("status") == "needs_human_review":
            review_queue.append(
                {
                    "id": decision["id"],
                    "app": decision["name"],
                    "agentReviewReasons": source.get("reviewReasons", []),
                    "humanDecision": decision["verdict"],
                    "finalConfidence": decision["confidence"],
                    "evidence": decision["evidence"],
                }
            )
    manifest = {
        "input": str(RAW_PATH.relative_to(ROOT)),
        "inputGeneratedAt": raw.get("generatedAt"),
        "output": str(OUTPUT_PATH.relative_to(ROOT)),
        "autoCleared": sum(row.get("status") == "researched" for row in raw_rows),
        "humanReviewCount": len(review_queue),
        "reviewQueue": review_queue,
    }
    atomic_write(MANIFEST_PATH, manifest)
    print(f"Wrote {len(reviewed)} reviewed rows and {len(review_queue)} review decisions")


if __name__ == "__main__":
    main()
