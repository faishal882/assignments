#!/usr/bin/env python3
"""Verify the 20-app audit sources in a real Chromium session via gstack browse."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts/browser-verification.json"
BROWSE_CANDIDATES = [
    ROOT / ".agents/skills/gstack/browse/dist/browse",
    Path.home() / ".codex/skills/gstack/browse/dist/browse",
    Path.home() / ".agents/skills/gstack/browse/dist/browse",
]


def browse_binary() -> Path:
    for candidate in BROWSE_CANDIDATES:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError("gstack browse is not installed; run its one-time setup first")


def run(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "GSTACK_CHROMIUM_NO_SANDBOX": "1"}
    return subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, timeout=timeout, check=False)


def technical_tokens(app: dict[str, Any]) -> list[str]:
    tokens = []
    auth = " ".join(app["auth"]).lower()
    for token in ("oauth", "api key", "token", "basic"):
        if token in auth:
            tokens.append(token)
    api = app["api"].lower()
    for token in ("rest", "graphql", "webhook", "cli"):
        if token in api:
            tokens.append(token)
    if app["mcp"] in {"Official", "Official beta"}:
        tokens.append("mcp")
    return list(dict.fromkeys(tokens))


def parse_json_line(output: str) -> dict[str, Any]:
    for line in reversed(output.splitlines()):
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    raise ValueError(f"No JSON browser result found in: {output[-500:]}")


def atomic_write(payload: object) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, OUTPUT)


def main() -> int:
    browser = browse_binary()
    verification = json.loads((ROOT / "data/verification.json").read_text(encoding="utf-8"))
    apps = {row["id"]: row for row in json.loads((ROOT / "data/apps.json").read_text(encoding="utf-8"))}
    results = []
    for index, sample in enumerate(verification["samples"], start=1):
        app = apps[sample["id"]]
        url = sample["sourceUrls"][0]
        navigation = run([str(browser), "goto", url])
        if navigation.returncode != 0:
            results.append({"appId": app["id"], "app": app["name"], "url": url, "loaded": False, "error": (navigation.stderr or navigation.stdout)[-1000:]})
            print(f"[browser-verify] {index}/20 {app['name']}: failed")
            continue
        tokens = technical_tokens(app)
        expression = (
            "(() => { const text = document.body.innerText.toLowerCase(); const tokens = "
            + json.dumps(tokens)
            + "; return JSON.stringify({title:document.title,finalUrl:location.href,textChars:text.length,"
              "tokenHits:Object.fromEntries(tokens.map(token => [token,text.includes(token)]))}); })()"
        )
        inspected = run([str(browser), "js", expression])
        try:
            details = parse_json_line(inspected.stdout)
            results.append({"appId": app["id"], "app": app["name"], "url": url, "loaded": True, "expectedTokens": tokens, **details})
            print(f"[browser-verify] {index}/20 {app['name']}: loaded")
        except ValueError as error:
            results.append({"appId": app["id"], "app": app["name"], "url": url, "loaded": True, "expectedTokens": tokens, "inspectionError": str(error)})
            print(f"[browser-verify] {index}/20 {app['name']}: inspection failed")

    loaded = sum(item["loaded"] for item in results)
    payload = {
        "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "method": "gstack browse persistent Chromium; page load plus deterministic technical-token presence check",
        "scope": "This proves browser accessibility and technical signals, not semantic support by itself; claim support remains in the human-readable ledger.",
        "summary": {"total": len(results), "loaded": loaded, "failed": len(results) - loaded},
        "results": results,
    }
    atomic_write(payload)
    print(json.dumps(payload["summary"], indent=2))
    return 0 if loaded >= 18 else 1


if __name__ == "__main__":
    raise SystemExit(main())
