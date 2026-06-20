"""Page an ArcGIS FeatureServer query into one GeoJSON FeatureCollection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request_page(url: str, parameters: dict) -> dict:
    request = Request(
        f"{url.rstrip('/')}/query",
        data=urlencode(parameters).encode(),
        headers={"User-Agent": "buildable-land-ingestion/1.0"},
    )
    with urlopen(request, timeout=120) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a bounded ArcGIS layer as GeoJSON")
    parser.add_argument("url", help="FeatureServer layer URL, including its numeric layer id")
    parser.add_argument("output", type=Path)
    parser.add_argument("--bbox", required=True, help="west,south,east,north in EPSG:4326")
    parser.add_argument("--where", default="1=1")
    parser.add_argument("--fields", default="*")
    parser.add_argument("--page-size", type=int, default=1000)
    args = parser.parse_args()

    features = []
    offset = 0
    while True:
        page = request_page(args.url, {
            "where": args.where,
            "geometry": args.bbox,
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": args.fields,
            "returnGeometry": "true",
            "outSR": 4326,
            "resultOffset": offset,
            "resultRecordCount": args.page_size,
            "f": "geojson",
        })
        batch = page.get("features", [])
        features.extend(batch)
        print(f"downloaded {len(features)} features")
        if len(batch) < args.page_size and not page.get("properties", {}).get("exceededTransferLimit"):
            break
        offset += len(batch)
        if not batch:
            raise RuntimeError("ArcGIS service reported more records but returned an empty page")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"type": "FeatureCollection", "features": features}))


if __name__ == "__main__":
    main()
