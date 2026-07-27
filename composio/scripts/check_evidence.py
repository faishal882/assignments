#!/usr/bin/env python3
"""Check primary evidence URLs concurrently and preserve an auditable report."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def check(row: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = row["evidence"][0]["url"]
    request = Request(url, headers={"User-Agent": "ToolkitRadarEvidenceCheck/2.0 (+case-study)"})
    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            status = int(response.status)
            final_url = response.url
        return {"id": row["id"], "name": row["name"], "url": url, "status": status,
                "finalUrl": final_url, "reachable": status < 500, "note": ""}
    except HTTPError as error:
        restricted = error.code in {401, 403, 405, 429}
        return {"id": row["id"], "name": row["name"], "url": url, "status": error.code,
                "finalUrl": error.url, "reachable": error.code < 500,
                "note": "Browser-accessible but automated request restricted" if restricted else str(error)}
    except (URLError, TimeoutError, OSError) as error:
        return {"id": row["id"], "name": row["name"], "url": url, "status": 0,
                "finalUrl": url, "reachable": False, "note": str(error)}


def atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/evidence-check.json")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    rows = json.loads((ROOT / "data/apps.json").read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.concurrency, 16))) as pool:
        futures = [pool.submit(check, row, args.timeout) for row in rows]
        for index, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            print(f"[evidence] {index}/{len(rows)}", end="\r")
    print()
    results.sort(key=lambda item: item["id"])
    summary = {
        "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(results),
        "reachable": sum(item["reachable"] for item in results),
        "success2xx": sum(200 <= item["status"] < 300 for item in results),
        "redirectsOrRestricted": sum(300 <= item["status"] < 500 for item in results),
        "failed": sum(not item["reachable"] for item in results),
    }
    atomic_write(output, {"summary": summary, "results": results})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
