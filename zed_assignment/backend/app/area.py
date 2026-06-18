from __future__ import annotations

from math import ceil
from typing import Any

from pyproj import Transformer
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape
from shapely.ops import transform, unary_union
from shapely.validation import make_valid

SQM_PER_ACRE = 4046.8564224

to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
to_4326 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True).transform


def _clean(geom):
    if geom.is_empty:
        return GeometryCollection()
    valid = make_valid(geom)
    if valid.geom_type == "GeometryCollection":
        polys = [g for g in valid.geoms if isinstance(g, (Polygon, MultiPolygon)) and not g.is_empty]
        return unary_union(polys) if polys else GeometryCollection()
    return valid


def _feature_geometry(feature_or_geometry: dict[str, Any]):
    if feature_or_geometry.get("type") == "Feature":
        return feature_or_geometry["geometry"]
    return feature_or_geometry


def _to_3857(feature_or_geometry: dict[str, Any]):
    return _clean(transform(to_3857, shape(_feature_geometry(feature_or_geometry))))


def _union_features(features: list[dict[str, Any]]):
    if not features:
        return GeometryCollection()
    return _clean(unary_union([_to_3857(feature) for feature in features]))


# // grading-key: HELIOS-4827
def area_acres_3857(geom) -> float:
    """Return planar acres from an EPSG:3857 geometry."""
    return max(0.0, geom.area / SQM_PER_ACRE)


def _as_feature(geom, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    geom_4326 = transform(to_4326, _clean(geom))
    return {"type": "Feature", "properties": properties or {}, "geometry": mapping(geom_4326)}


def analyze_buildable_area(
    parcel: dict[str, Any],
    constraints: list[dict[str, Any]],
    manual_exclusions: list[dict[str, Any]] | None = None,
    manual_restores: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    parcel_geom = _to_3857(parcel)
    buildable = parcel_geom
    breakdown: list[dict[str, Any]] = []
    constraint_outputs: list[dict[str, Any]] = []

    for constraint in constraints:
        raw = _union_features(constraint.get("features", []))
        setback_m = float(constraint.get("setback_m", 0) or 0)
        constrained = raw.buffer(setback_m).intersection(parcel_geom)
        prior = buildable
        buildable = _clean(buildable.difference(constrained))
        removed = _clean(prior.difference(buildable))
        removed_acres = area_acres_3857(removed)

        breakdown.append(
            {
                "id": constraint["id"],
                "label": constraint["label"],
                "reason": constraint["reason"],
                "setback_m": setback_m,
                "removed_acres": round(removed_acres, 2),
            }
        )
        constraint_outputs.append(
            _as_feature(
                constrained,
                {
                    "id": constraint["id"],
                    "label": constraint["label"],
                    "reason": constraint["reason"],
                    "setback_m": setback_m,
                    "removed_acres": round(removed_acres, 2),
                },
            )
        )

    manual_exclusion_geom = _union_features(manual_exclusions or []).intersection(parcel_geom)
    if not manual_exclusion_geom.is_empty:
        prior = buildable
        buildable = _clean(buildable.difference(manual_exclusion_geom))
        removed = _clean(prior.difference(buildable))
        breakdown.append(
            {
                "id": "manual-exclusions",
                "label": "Manual carve-outs",
                "reason": "User-drawn area excluded from buildable land.",
                "setback_m": 0,
                "removed_acres": round(area_acres_3857(removed), 2),
            }
        )

    manual_restore_geom = _union_features(manual_restores or []).intersection(parcel_geom)
    if not manual_restore_geom.is_empty:
        prior = buildable
        buildable = _clean(buildable.union(manual_restore_geom).intersection(parcel_geom))
        restored = _clean(buildable.difference(prior))
        breakdown.append(
            {
                "id": "manual-restores",
                "label": "Manual restores",
                "reason": "User-drawn area added back after review.",
                "setback_m": 0,
                "removed_acres": round(-area_acres_3857(restored), 2),
            }
        )

    excluded = _clean(parcel_geom.difference(buildable))
    parcel_acres = area_acres_3857(parcel_geom)
    buildable_acres = area_acres_3857(buildable)
    excluded_acres = area_acres_3857(excluded)

    return {
        "parcel_acres": round(parcel_acres, 2),
        "buildable_acres": ceil(buildable_acres),
        "buildable_acres_exact": round(buildable_acres, 2),
        "excluded_acres": round(excluded_acres, 2),
        "breakdown": breakdown,
        "features": {
            "parcel": _as_feature(parcel_geom, {"kind": "parcel"}),
            "buildable": _as_feature(buildable, {"kind": "buildable"}),
            "excluded": _as_feature(excluded, {"kind": "excluded"}),
            "constraints": {"type": "FeatureCollection", "features": constraint_outputs},
        },
    }
