"""Package normalized county constraint GeoJSON as a single PMTiles archive."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def require_command(name: str) -> str:
    command = shutil.which(name)
    if not command:
        raise SystemExit(f"{name} is required and was not found on PATH")
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description="Build county-scale constraint vector tiles")
    parser.add_argument("--output", type=Path, required=True, help="Output .pmtiles archive")
    parser.add_argument("--wetlands", type=Path)
    parser.add_argument("--floodplain", type=Path)
    parser.add_argument("--transmission", type=Path)
    parser.add_argument("--minimum-zoom", type=int, default=8)
    parser.add_argument("--maximum-zoom", type=int, default=16)
    args = parser.parse_args()

    layers = [
        (name, path)
        for name, path in (
            ("wetlands", args.wetlands),
            ("floodplain", args.floodplain),
            ("transmission", args.transmission),
        )
        if path
    ]
    if not layers:
        raise SystemExit("Provide at least one constraint GeoJSON layer")

    tippecanoe = require_command("tippecanoe")
    pmtiles = require_command("pmtiles")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary_directory:
        mbtiles = Path(temporary_directory) / "constraints.mbtiles"
        command = [
            tippecanoe,
            "--output", str(mbtiles),
            "--minimum-zoom", str(args.minimum_zoom),
            "--maximum-zoom", str(args.maximum_zoom),
            "--drop-densest-as-needed",
            "--extend-zooms-if-still-dropping",
            "--force",
        ]
        for name, path in layers:
            command.extend(["-L", f"{name}:{path}"])
        subprocess.run(command, check=True)
        subprocess.run([pmtiles, "convert", str(mbtiles), str(args.output)], check=True)
    print(f"tiles: {', '.join(name for name, _ in layers)} -> {args.output}")


if __name__ == "__main__":
    main()
