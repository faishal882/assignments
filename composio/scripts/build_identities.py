#!/usr/bin/env python3
"""Build the agent identity registry only from the supplied assignment brief."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / "AI Product Ops Intern -The take-home assignment.md"
SEED = ROOT / "data/apps-seed.json"
OUTPUT = ROOT / "data/app-identities.json"

MANUAL_DISAMBIGUATION = {
    8: {"hosts": ["close.com"], "reason": "Exact company from the supplied close.com hint."},
    17: {"hosts": ["plain.com"], "reason": "Exact support product from the supplied plain.com hint."},
    50: {"hosts": ["fanbasis.com"], "reason": "Capitalization normalized from the supplied fanbasis.com hint."},
    58: {"hosts": ["github.com"], "urlContains": ["sherlock-project/sherlock"], "reason": "Repository path supplied in the brief."},
    84: {"hosts": ["gopaygent.com"], "reason": "The brief identifies Paygent Connect as the NMI-powered payments product."},
    85: {"hosts": ["ipayx.ai"], "reason": "Exact domain supplied in the brief; do not substitute IXOPAY."},
    91: {"hosts": ["cloud.google.com"], "urlContains": ["notebooklm", "gemini"], "reason": "Enterprise NotebookLM hint supplied in the brief."},
    98: {"hosts": ["github.com"], "urlContains": ["mermaid-js/mermaid-cli"], "reason": "Repository path supplied in the brief."},
    99: {"hosts": ["transcriptapi.com"], "reason": "Exact vendor domain supplied in the brief."},
}


def atomic_write(path: Path, payload: object) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def extract_urls(cell: str) -> list[str]:
    markdown_urls = re.findall(r"\((https?://[^)]+)\)", cell)
    if markdown_urls:
        return list(dict.fromkeys(url.rstrip("/).") for url in markdown_urls))
    plain_cell = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", cell)
    bare_domains = re.findall(
        r"(?<![/\w.-])((?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]*)?)",
        plain_cell,
        flags=re.I,
    )
    return list(dict.fromkeys(f"https://{value.rstrip('/).')}" for value in bare_domains))


def main() -> None:
    text = BRIEF.read_text(encoding="utf-8")
    table_rows: dict[int, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\|\s*(\d{1,3})\s*\|.*?\|\s*(.*?)\s*\|$", line)
        if match:
            table_rows[int(match.group(1))] = match.group(2)

    groups = json.loads(SEED.read_text(encoding="utf-8"))
    seeded = [(group["category"], app) for group in groups for app in group["apps"]]
    if len(seeded) != 100 or set(table_rows) != set(range(1, 101)):
        raise ValueError(f"Expected 100 seed and brief rows, got {len(seeded)} and {len(table_rows)}")

    identities = []
    for app_id, (category, app) in enumerate(seeded, start=1):
        hint = table_rows[app_id]
        hint_urls = extract_urls(hint)
        hosts = []
        for url in hint_urls:
            host = (urlparse(url).hostname or "").lower().removeprefix("www.")
            if host:
                hosts.append(host)
        override = MANUAL_DISAMBIGUATION.get(app_id, {})
        if override.get("hosts"):
            hosts = override["hosts"]
        hosts = list(dict.fromkeys(hosts))
        if not hosts:
            raise ValueError(f"No official host found in brief for {app_id}: {app} ({hint})")
        identities.append(
            {
                "id": app_id,
                "app": app,
                "category": category,
                "briefHint": re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", hint),
                "hintUrls": hint_urls,
                "hosts": hosts,
                "urlContains": override.get("urlContains", []),
                "source": "assignment_brief",
                **({"disambiguation": override["reason"]} if override.get("reason") else {}),
            }
        )

    atomic_write(OUTPUT, identities)
    print(f"Wrote {len(identities)} brief-derived identities to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
