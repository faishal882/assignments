from pyproj import Transformer
from shapely.geometry import Polygon, mapping

from app.area import SQM_PER_ACRE, analyze_buildable_area, area_acres
from app.sample_data import PARCELS, REAL_PAIR


def feature(geometry):
    return {"type": "Feature", "properties": {}, "geometry": mapping(geometry)}


def utm_square_feature(size_m=100.0):
    inverse = Transformer.from_crs("EPSG:32614", "EPSG:4326", always_xy=True).transform
    x, y = 620_000, 3_350_000
    coordinates = [
        inverse(x, y),
        inverse(x + size_m, y),
        inverse(x + size_m, y + size_m),
        inverse(x, y + size_m),
        inverse(x, y),
    ]
    return feature(Polygon(coordinates))


def constraint(layer_id, geometry, setback_m=0):
    return {
        "id": layer_id,
        "label": layer_id.title(),
        "reason": "Synthetic geometry",
        "setback_m": setback_m,
        "features": [geometry],
    }


def test_area_acres_uses_projected_square_meters():
    class Square:
        area = SQM_PER_ACRE * 2.25

    assert area_acres(Square()) == 2.25


def test_local_utm_area_is_accurate_and_not_rounded_up():
    result = analyze_buildable_area(utm_square_feature(), [])

    assert result["analysis_crs"] == "EPSG:32614"
    assert result["parcel_acres"] == 2.47
    assert result["buildable_acres"] == 2.47
    assert result["excluded_acres"] == 0


def test_overlapping_layers_are_attributed_without_double_counting():
    parcel = utm_square_feature(100)
    left = utm_square_feature(70)
    # Same exclusion twice guarantees complete overlap for layer two.
    result = analyze_buildable_area(
        parcel,
        [constraint("first", left), constraint("second", left)],
    )

    first, second = result["breakdown"]
    assert first["removed_acres"] > 0
    assert second["removed_acres"] == 0
    assert second["overlap_acres"] == second["gross_acres"]
    assert result["overlap_diagnostics"]["duplicate_overlap_acres"] > 0
    assert abs(sum(row["removed_acres"] for row in result["breakdown"]) - result["excluded_acres"]) <= 0.01


def test_restore_is_clipped_to_parcel_and_reconciles_totals():
    parcel = PARCELS["TRAVIS-DEMO-001"]
    base = analyze_buildable_area(parcel, [constraint("all", parcel)])
    restored = analyze_buildable_area(parcel, [constraint("all", parcel)], manual_restores=[parcel])

    assert base["buildable_acres"] == 0
    assert restored["excluded_acres"] == 0
    assert restored["buildable_acres"] == restored["parcel_acres"]
    assert restored["breakdown"][-1]["removed_acres"] < 0


def test_invalid_bowtie_geometry_is_repaired():
    parcel = PARCELS["TRAVIS-DEMO-001"]
    bowtie = feature(Polygon([
        (-97.74, 30.271), (-97.73, 30.279), (-97.74, 30.279),
        (-97.73, 30.271), (-97.74, 30.271),
    ]))

    result = analyze_buildable_area(parcel, [constraint("messy", bowtie)])
    assert result["excluded_acres"] > 0


def test_real_public_parcel_and_nwi_pair_analyzes_without_topology_failure():
    result = analyze_buildable_area(
        REAL_PAIR["parcel"],
        [constraint("nwi-real", REAL_PAIR["wetland"], setback_m=15.24)],
    )

    assert REAL_PAIR["provenance"]["parcel_id"] == "0315310103"
    assert REAL_PAIR["provenance"]["wetland_object_id"] == 6214742
    assert result["analysis_crs"] == "EPSG:32614"
    assert result["parcel_acres"] > 100
    assert result["excluded_acres"] > 1
    assert abs(
        result["buildable_acres"] + result["excluded_acres"] - result["parcel_acres"]
    ) <= 0.01
