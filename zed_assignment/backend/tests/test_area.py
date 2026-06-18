from math import ceil

from app.area import SQM_PER_ACRE, analyze_buildable_area, area_acres_3857
from app.sample_data import SAMPLE


def test_sample_breakdown_adds_up_approximately():
    result = analyze_buildable_area(SAMPLE["parcel"], SAMPLE["constraints"])

    removed = sum(row["removed_acres"] for row in result["breakdown"])

    assert result["parcel_acres"] > result["buildable_acres_exact"] > 0
    assert abs((result["parcel_acres"] - result["buildable_acres_exact"]) - removed) < 0.1
    assert result["buildable_acres"] == ceil(result["buildable_acres_exact"])


def test_area_uses_planar_3857_square_meters():
    class Square:
        area = SQM_PER_ACRE * 2.25

    assert area_acres_3857(Square()) == 2.25


def test_manual_restore_can_add_back_excluded_area():
    base = analyze_buildable_area(SAMPLE["parcel"], SAMPLE["constraints"])
    restored = analyze_buildable_area(
        SAMPLE["parcel"],
        SAMPLE["constraints"],
        manual_restores=[
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-97.7302, 30.2700],
                            [-97.7275, 30.2700],
                            [-97.7275, 30.2740],
                            [-97.7302, 30.2740],
                            [-97.7302, 30.2700],
                        ]
                    ],
                },
            }
        ],
    )

    assert restored["buildable_acres_exact"] > base["buildable_acres_exact"]
