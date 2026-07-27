#!/usr/bin/env python3
"""Resumable, evidence-scored toolkit research through the signed-in Composio CLI."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
IDENTITIES_PATH = ROOT / "data/app-identities.json"
DEFAULT_OUTPUT = ROOT / "artifacts/research.latest.json"
SEARCH_TOOL = "COMPOSIO_SEARCH_WEB"

@dataclass(frozen=True)
class AppIdentity:
    id: int
    app: str
    category: str
    hosts: tuple[str, ...]
    url_contains: tuple[str, ...] = ()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def normalize_host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def host_matches(host: str, expected: str) -> bool:
    normalized = host.removeprefix("www.").lower()
    target = expected.removeprefix("www.").lower()
    return normalized == target or normalized.endswith(f".{target}")


def citation_matches_identity(citation: dict[str, Any], identity: AppIdentity) -> bool:
    url = str(citation.get("url", ""))
    host = normalize_host(url)
    if not host or not any(host_matches(host, expected) for expected in identity.hosts):
        return False
    if identity.url_contains:
        lowered = url.lower()
        return any(fragment.lower() in lowered for fragment in identity.url_contains)
    return True


def score_citation(citation: dict[str, Any], identity: AppIdentity) -> int:
    url = str(citation.get("url", ""))
    title = str(citation.get("title", ""))
    score = 0
    if url.startswith("https://"):
        score += 1
    if citation_matches_identity(citation, identity):
        score += 6
    documentation_terms = ("/docs", "developer", "developers", "api", "auth", "oauth", "reference")
    if any(term in f"{title} {url}".lower() for term in documentation_terms):
        score += 2
    app_tokens = [token for token in identity.app.lower().replace(".", " ").split() if len(token) > 2]
    haystack = f"{title} {url}".lower()
    if app_tokens and any(token in haystack for token in app_tokens):
        score += 2
    return score


def citation_is_technical_evidence(citation: dict[str, Any], identity: AppIdentity) -> bool:
    if not citation_matches_identity(citation, identity):
        return False
    url = str(citation.get("url", "")).lower()
    title = str(citation.get("title", "")).lower()
    if "/blog/" in url:
        return False
    if identity.url_contains and "github.com" in identity.hosts:
        return True
    technical_terms = (
        "/docs", "developer", "developers", "api", "auth", "oauth", "reference",
        "webhook", "graphql", "mcp", "open source", "github.com",
    )
    return any(term in f"{title} {url}" for term in technical_terms)


def classify_result(
    identity: AppIdentity,
    answer: str,
    citations: list[dict[str, Any]],
    errors: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any] | None]:
    ranked = sorted(
        (
            {
                **citation,
                "score": score_citation(citation, identity),
                "official": citation_matches_identity(citation, identity),
                "technical": citation_is_technical_evidence(citation, identity),
            }
            for citation in citations
        ),
        key=lambda item: (-int(item["score"]), str(item.get("url", ""))),
    )
    review_reasons: list[str] = []
    if len(answer) < 120:
        review_reasons.append("low_answer_signal")
    if not ranked:
        review_reasons.append("no_citations")
    if not any(item["official"] for item in ranked):
        review_reasons.append("no_official_identity_match")
    elif not any(item["official"] and item["technical"] for item in ranked):
        review_reasons.append("no_official_technical_evidence")
    if errors and not answer:
        review_reasons.append("search_failed")
    primary = next(
        (item for item in ranked if item["official"] and item["technical"]),
        next((item for item in ranked if item["official"]), ranked[0] if ranked else None),
    )
    return ranked, review_reasons, primary


def build_query(identity: AppIdentity) -> str:
    domains = ", ".join(identity.hosts) or "the provider's official domain"
    path_guard = (
        f" Required URL identity fragments: {', '.join(identity.url_contains)}."
        if identity.url_contains
        else ""
    )
    return (
        f'Research the exact product "{identity.app}" in the category '
        f'"{identity.category}". Treat {domains} as its expected official source domain(s).'
        f"{path_guard} Do not substitute a similarly named company or product. Find provider-owned "
        "documentation for authentication (OAuth, API key, Basic, token), developer signup and "
        "access gates (free trial, paid plan, admin, review, partner, contact sales), API style "
        "(REST, GraphQL, webhooks, CLI), and an official first-party MCP server. Clearly state "
        "unknown when direct evidence is absent. Prefer provider-owned documentation and include URLs."
    )


def _find_search_payload(value: Any) -> dict[str, Any]:
    """Locate answer/citations across CLI envelope variations."""
    if isinstance(value, dict):
        if isinstance(value.get("answer"), str) or isinstance(value.get("citations"), list):
            return value
        for key in ("data", "result", "output", "response"):
            if key in value:
                found = _find_search_payload(value[key])
                if found:
                    return found
        for child in value.values():
            found = _find_search_payload(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_search_payload(child)
            if found:
                return found
    return {}


def parse_cli_output(stdout: str) -> tuple[str, list[dict[str, Any]]]:
    text = stdout.strip()
    candidates = [text]
    candidates.extend(line for line in reversed(text.splitlines()) if line.strip().startswith(("{", "[")))
    decoded: Any = None
    for candidate in candidates:
        try:
            decoded = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if decoded is None:
        raise ValueError("Composio CLI did not return JSON")
    payload = _find_search_payload(decoded)
    answer = payload.get("answer", "")
    citations = payload.get("citations", [])
    if not isinstance(answer, str):
        answer = str(answer or "")
    if not isinstance(citations, list):
        citations = []
    clean = [item for item in citations if isinstance(item, dict) and str(item.get("url", "")).startswith("http")]
    return answer.strip(), clean


def execute_search(query: str, timeout: int) -> tuple[str, list[dict[str, Any]]]:
    command = [
        "composio",
        "execute",
        SEARCH_TOOL,
        "-d",
        json.dumps({"query": query}, separators=(",", ":")),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[-1000:]
        raise RuntimeError(f"Composio exited {completed.returncode}: {detail}")
    return parse_cli_output(completed.stdout)


def research_one(
    identity: AppIdentity, max_attempts: int, timeout: int
) -> dict[str, Any]:
    query = build_query(identity)
    errors: list[str] = []
    answer = ""
    citations: list[dict[str, Any]] = []
    attempts = 0
    for attempts in range(1, max_attempts + 1):
        try:
            answer, citations = execute_search(query, timeout)
            if not answer and not citations:
                raise ValueError("empty answer and citations")
            break
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            errors.append(f"attempt {attempts}: {error}")
            if attempts < max_attempts:
                time.sleep(min(8.0, (2 ** (attempts - 1)) + random.random()))

    ranked, review_reasons, primary = classify_result(identity, answer, citations, errors)
    return {
        "id": identity.id,
        "app": identity.app,
        "category": identity.category,
        "query": query,
        "identity": {"hosts": list(identity.hosts), "urlContains": list(identity.url_contains)},
        "researchedAt": utc_now(),
        "attempts": attempts,
        "answer": answer,
        "citations": ranked,
        "primaryEvidence": primary,
        "evidenceScore": sum(int(item["score"]) for item in ranked[:3]),
        "status": "needs_human_review" if review_reasons else "researched",
        "reviewReasons": review_reasons,
        **({"errors": errors} if errors else {}),
    }


def load_identities() -> list[AppIdentity]:
    rows = json.loads(IDENTITIES_PATH.read_text(encoding="utf-8"))
    return [
        AppIdentity(
            id=int(row["id"]),
            app=row["app"],
            category=row["category"],
            hosts=tuple(row["hosts"]),
            url_contains=tuple(row.get("urlContains", [])),
        )
        for row in rows
    ]


def build_artifact(rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: row["id"])
    return {
        "generatedAt": utc_now(),
        "method": "Python orchestrator + signed-in Composio CLI COMPOSIO_SEARCH_WEB",
        "agentVersion": 2,
        "offset": args.offset,
        "requested": args.limit,
        "completed": len(ordered),
        "researched": sum(row["status"] == "researched" for row in ordered),
        "needsHumanReview": sum(row["status"] == "needs_human_review" for row in ordered),
        "rows": ordered,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true", help="Skip IDs already present in the output artifact")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.limit = max(0, min(100, args.limit))
    args.offset = max(0, args.offset)
    args.concurrency = max(1, min(8, args.concurrency))
    args.max_attempts = max(1, min(5, args.max_attempts))
    output = args.output if args.output.is_absolute() else ROOT / args.output

    selected = load_identities()[args.offset : args.offset + args.limit]
    prior_rows: dict[int, dict[str, Any]] = {}
    selected_ids = {identity.id for identity in selected}
    if args.resume and output.exists():
        prior = json.loads(output.read_text(encoding="utf-8"))
        prior_rows = {
            int(row["id"]): row
            for row in prior.get("rows", [])
            if int(row["id"]) in selected_ids
        }
        identities_by_id = {identity.id: identity for identity in selected}
        for row_id, row in prior_rows.items():
            ranked, reasons, primary = classify_result(
                identities_by_id[row_id],
                str(row.get("answer", "")),
                list(row.get("citations", [])),
                list(row.get("errors", [])),
            )
            row["citations"] = ranked
            row["primaryEvidence"] = primary
            row["evidenceScore"] = sum(int(item["score"]) for item in ranked[:3])
            row["reviewReasons"] = reasons
            row["status"] = "needs_human_review" if reasons else "researched"
    pending = [identity for identity in selected if identity.id not in prior_rows]
    rows = dict(prior_rows)

    if pending:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {
                pool.submit(research_one, identity, args.max_attempts, args.timeout): identity
                for identity in pending
            }
            done = 0
            for future in as_completed(futures):
                identity = futures[future]
                try:
                    row = future.result()
                except Exception as error:  # keep the checkpoint usable after an unexpected worker error
                    row = {
                        "id": identity.id,
                        "app": identity.app,
                        "category": identity.category,
                        "query": build_query(identity),
                        "researchedAt": utc_now(),
                        "answer": "",
                        "citations": [],
                        "status": "needs_human_review",
                        "reviewReasons": ["unexpected_worker_error"],
                        "errors": [str(error)],
                    }
                rows[identity.id] = row
                done += 1
                atomic_write_json(output, build_artifact(list(rows.values()), args))
                print(f"[research] {done}/{len(pending)} {identity.app}: {row['status']}", file=sys.stderr)

    artifact = build_artifact(list(rows.values()), args)
    atomic_write_json(output, artifact)
    print(
        json.dumps(
            {
                "output": str(output.relative_to(ROOT) if output.is_relative_to(ROOT) else output),
                "rows": artifact["completed"],
                "researched": artifact["researched"],
                "needsHumanReview": artifact["needsHumanReview"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
