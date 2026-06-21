"""Build the runtime spatial catalog from normalized GeoJSON exports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from shapely.geometry import box, mapping, shape
from shapely.validation import make_valid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.spatial_store import SpatialStore  # noqa: E402


def read_clipped(path: Path, clip_bounds=None):
    payload = json.loads(path.read_text())
    clip = box(*clip_bounds) if clip_bounds else None
    for feature in payload.get("features", []):
        geometry = make_valid(shape(feature.get("geometry")))
        if clip:
            geometry = geometry.intersection(clip)
        if geometry.is_empty:
            continue
        yield {**feature, "geometry": mapping(geometry)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an indexed SQLite spatial catalog")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--parcels", type=Path, required=True)
    parser.add_argument("--wetlands", type=Path)
    parser.add_argument("--floodplain", type=Path)
    parser.add_argument("--transmission", type=Path)
    parser.add_argument("--clip", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--region-id", default="county", help="Stable county or acquisition-region identifier")
    parser.add_argument("--display-tolerance", type=float, default=0.00001, help="WGS84 simplification tolerance for display copies")
    args = parser.parse_args()

    if args.database.exists():
        args.database.unlink()
    store = SpatialStore(args.database)
    store.initialize()
    parcel_features = list(read_clipped(args.parcels, args.clip))
    constraint_paths = {
        "wetlands": args.wetlands,
        "floodplain": args.floodplain,
        "transmission": args.transmission,
    }
    constraint_features = {
        layer_id: list(read_clipped(path, args.clip)) if path else []
        for layer_id, path in constraint_paths.items()
    }
    parcels = store.replace_parcels(parcel_features)
    constraint_counts = {
        layer_id: store.replace_constraints(
            layer_id,
            features,
            region_id=args.region_id,
            display_tolerance=args.display_tolerance,
        )
        for layer_id, features in constraint_features.items()
    }
    featured_parcel_id = None
    wetland_features = constraint_features["wetlands"]
    if wetland_features:
        wetland_union = shape(wetland_features[0]["geometry"])
        for feature in wetland_features[1:]:
            wetland_union = wetland_union.union(shape(feature["geometry"]))
        with store.connect() as connection:
            candidates = connection.execute("SELECT id, geometry FROM parcels").fetchall()
        scored = [
            (shape(json.loads(row["geometry"])).intersection(wetland_union).area, row["id"])
            for row in candidates
        ]
        featured_parcel_id = max(scored, default=(0, None))[1]
    with store.connect() as connection:
        connection.executemany(
            "INSERT OR REPLACE INTO metadata VALUES (?, ?)",
            [
                ("parcel_source", "TxGIO/TNRIS standardized Bell County parcels"),
                ("wetlands_source", "USFWS National Wetlands Inventory Version 2"),
                ("clip_bounds", json.dumps(args.clip)),
                ("region_id", args.region_id),
                ("display_tolerance", str(args.display_tolerance)),
                ("featured_parcel_id", featured_parcel_id or ""),
            ],
        )
    counts = ", ".join(f"{count} {layer_id}" for layer_id, count in constraint_counts.items())
    print(f"catalog: {parcels} parcels, {counts} -> {args.database}")


if __name__ == "__main__":
    main()
