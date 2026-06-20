"""Readable GeoJSON ingestion path for replacing the checked-in demo adapter.

Large shapefiles should first be converted with ogr2ogr; keeping GDAL outside the
Python runtime makes the application install deterministic for reviewers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform
from shapely.validation import make_valid


def ingest(layer_id: str, argv=None) -> None:
    parser = argparse.ArgumentParser(description=f"Normalize {layer_id} GeoJSON")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-crs", default="EPSG:4326")
    args = parser.parse_args(argv)

    payload = json.loads(args.input.read_text())
    features = payload.get("features", [])
    project = Transformer.from_crs(args.source_crs, "EPSG:4326", always_xy=True).transform
    normalized = []
    repaired = skipped = 0
    for feature in features:
        geometry = shape(feature.get("geometry"))
        if geometry.is_empty:
            skipped += 1
            continue
        if not geometry.is_valid:
            geometry = make_valid(geometry)
            repaired += 1
        geometry = transform(project, geometry)
        normalized.append({**feature, "geometry": mapping(geometry)})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"type": "FeatureCollection", "features": normalized}))
    print(f"{layer_id}: wrote {len(normalized)} features; repaired {repaired}; skipped {skipped}")
