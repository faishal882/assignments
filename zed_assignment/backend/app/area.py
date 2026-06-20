"""Buildable-area geometry engine.

Inputs and outputs use WGS84 GeoJSON (EPSG:4326). Every buffer and acreage
calculation is performed in the local UTM zone selected from the parcel
centroid. UTM is used because it preserves local distances and areas closely
enough for parcel-scale planning; Web Mercator (EPSG:3857) is intentionally
never used for measurement. Acreage values are rounded to two decimals only at
the API boundary while reconciliation uses full-precision projected areas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from pyproj import CRS, Transformer
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape
from shapely.ops import transform, unary_union
from shapely.validation import make_valid

SQM_PER_ACRE = 4046.8564224
GeoJSON = dict[str, Any]


@dataclass(frozen=True)
class AnalysisProjection:
    crs: CRS
    forward: Any
    inverse: Any


def _polygonal(geometry):
    """Repair a geometry and retain only polygonal output when required."""
    if geometry.is_empty:
        return GeometryCollection()
    valid = make_valid(geometry)
    if valid.geom_type == "GeometryCollection":
        parts = [
            part
            for part in valid.geoms
            if isinstance(part, (Polygon, MultiPolygon)) and not part.is_empty
        ]
        return unary_union(parts) if parts else GeometryCollection()
    return valid


def _geometry(value: GeoJSON):
    geometry = value.get("geometry") if value.get("type") == "Feature" else value
    if not geometry:
        raise ValueError("GeoJSON must contain a geometry")
    return shape(geometry)


def _projection_for(parcel_wgs84) -> AnalysisProjection:
    centroid = parcel_wgs84.centroid
    zone = min(60, max(1, int((centroid.x + 180) // 6) + 1))
    epsg = (32600 if centroid.y >= 0 else 32700) + zone
    crs = CRS.from_epsg(epsg)
    return AnalysisProjection(
        crs=crs,
        forward=Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform,
        inverse=Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform,
    )


def _project(value: GeoJSON, projection: AnalysisProjection):
    return _polygonal(transform(projection.forward, _geometry(value)))


def _union(values: Iterable[GeoJSON], projection: AnalysisProjection):
    geometries = [_project(value, projection) for value in values]
    return _polygonal(unary_union(geometries)) if geometries else GeometryCollection()


def area_acres(geometry) -> float:
    """Return acres for a geometry already projected in a metric local CRS."""
    return max(0.0, geometry.area / SQM_PER_ACRE)


def _feature(geometry, projection: AnalysisProjection, properties=None) -> GeoJSON:
    wgs84 = transform(projection.inverse, _polygonal(geometry))
    return {
        "type": "Feature",
        "properties": properties or {},
        "geometry": mapping(wgs84),
    }


def analyze_buildable_area(
    parcel: GeoJSON,
    constraints: list[dict[str, Any]],
    manual_exclusions: list[GeoJSON] | None = None,
    manual_restores: list[GeoJSON] | None = None,
) -> dict[str, Any]:
    """Analyze a parcel using ordered, non-double-counted constraint attribution.

    Constraint features are repaired, projected, buffered in metres, and clipped
    to the parcel. ``removed_acres`` is each layer's incremental contribution in
    request order, so those values can be summed. ``gross_acres`` and
    ``overlap_acres`` are diagnostic values and must not be summed.
    """
    parcel_wgs84 = _polygonal(_geometry(parcel))
    if parcel_wgs84.is_empty or parcel_wgs84.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Parcel must contain a non-empty Polygon or MultiPolygon")

    projection = _projection_for(parcel_wgs84)
    parcel_geometry = _polygonal(transform(projection.forward, parcel_wgs84))
    buildable = parcel_geometry
    attributed_union = GeometryCollection()
    breakdown: list[dict[str, Any]] = []
    constraint_features: list[GeoJSON] = []
    clipped_layers = []

    for constraint in constraints:
        raw = _union(constraint.get("features", []), projection)
        setback_m = float(constraint.get("setback_m", 0) or 0)
        clipped = _polygonal(raw.buffer(setback_m).intersection(parcel_geometry))
        incremental = _polygonal(clipped.difference(attributed_union))
        overlap = _polygonal(clipped.intersection(attributed_union))
        attributed_union = _polygonal(attributed_union.union(clipped))
        buildable = _polygonal(buildable.difference(clipped))
        clipped_layers.append(clipped)

        row = {
            "id": constraint["id"],
            "label": constraint["label"],
            "reason": constraint["reason"],
            "setback_m": setback_m,
            "removed_acres": round(area_acres(incremental), 2),
            "gross_acres": round(area_acres(clipped), 2),
            "overlap_acres": round(area_acres(overlap), 2),
        }
        breakdown.append(row)
        constraint_features.append(_feature(clipped, projection, row))

    automatic_union = _polygonal(unary_union(clipped_layers)) if clipped_layers else GeometryCollection()
    gross_sum = sum(area_acres(item) for item in clipped_layers)
    duplicate_overlap = max(0.0, gross_sum - area_acres(automatic_union))

    carve_geometry = _polygonal(
        _union(manual_exclusions or [], projection).intersection(parcel_geometry)
    )
    if not carve_geometry.is_empty:
        incremental = _polygonal(carve_geometry.intersection(buildable))
        buildable = _polygonal(buildable.difference(carve_geometry))
        breakdown.append(
            {
                "id": "manual-exclusions",
                "label": "Manual carve-outs",
                "reason": "User-drawn area removed from otherwise buildable land.",
                "setback_m": 0.0,
                "removed_acres": round(area_acres(incremental), 2),
                "gross_acres": round(area_acres(carve_geometry), 2),
                "overlap_acres": round(area_acres(carve_geometry.difference(incremental)), 2),
            }
        )

    restore_geometry = _polygonal(
        _union(manual_restores or [], projection).intersection(parcel_geometry)
    )
    if not restore_geometry.is_empty:
        restored = _polygonal(restore_geometry.difference(buildable))
        buildable = _polygonal(buildable.union(restore_geometry).intersection(parcel_geometry))
        breakdown.append(
            {
                "id": "manual-restores",
                "label": "Manual restores",
                "reason": "User-drawn area restored inside the parcel boundary.",
                "setback_m": 0.0,
                "removed_acres": round(-area_acres(restored), 2),
                "gross_acres": round(area_acres(restore_geometry), 2),
                "overlap_acres": 0.0,
            }
        )

    excluded = _polygonal(parcel_geometry.difference(buildable))
    return {
        "analysis_crs": projection.crs.to_string(),
        "area_method": "Local UTM planar measurement; results rounded to 0.01 acre",
        "parcel_acres": round(area_acres(parcel_geometry), 2),
        "buildable_acres": round(area_acres(buildable), 2),
        "excluded_acres": round(area_acres(excluded), 2),
        "breakdown": breakdown,
        "overlap_diagnostics": {
            "automatic_union_acres": round(area_acres(automatic_union), 2),
            "duplicate_overlap_acres": round(duplicate_overlap, 2),
            "note": "Gross and overlap values are diagnostic; sum only removed_acres.",
        },
        "features": {
            "parcel": _feature(parcel_geometry, projection, {"kind": "parcel"}),
            "buildable": _feature(buildable, projection, {"kind": "buildable"}),
            "excluded": _feature(excluded, projection, {"kind": "excluded"}),
            "constraints": {"type": "FeatureCollection", "features": constraint_features},
            "manual_exclusions": _feature(carve_geometry, projection, {"kind": "carve-out"}),
            "manual_restores": _feature(restore_geometry, projection, {"kind": "restore"}),
        },
    }
