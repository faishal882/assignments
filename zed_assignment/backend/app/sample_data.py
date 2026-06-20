import json
from pathlib import Path

REAL_PAIR = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "travis_real_pair.json").read_text()
)

PARCELS = {
    "TCAD-0315310103": REAL_PAIR["parcel"],
    "TRAVIS-DEMO-001": {
        "type": "Feature",
        "properties": {
            "id": "TRAVIS-DEMO-001",
            "name": "Colorado Bend demo parcel",
            "address": "100 Demo Tract, Austin, TX",
            "county": "Travis",
            "source_note": "Demo fixture shaped to exercise public-data workflows; replace with TNRIS county parcels for production runs.",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-97.7426, 30.2692],
                    [-97.7258, 30.2692],
                    [-97.7258, 30.2818],
                    [-97.7426, 30.2818],
                    [-97.7426, 30.2692],
                ]
            ],
        },
    }
}

SOURCE_FEATURES = {
    "wetlands": [
                REAL_PAIR["wetland"],
                {
                    "type": "Feature",
                    "properties": {"source": "USFWS NWI"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-97.7389, 30.2707],
                                [-97.7354, 30.2706],
                                [-97.7339, 30.2749],
                                [-97.7368, 30.2771],
                                [-97.7402, 30.2747],
                                [-97.7389, 30.2707],
                            ]
                        ],
                    },
                }
    ],
    "floodplain": [
                {
                    "type": "Feature",
                    "properties": {"source": "FEMA NFHL"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-97.7315, 30.2692],
                                [-97.7258, 30.2692],
                                [-97.7258, 30.2818],
                                [-97.7303, 30.2818],
                                [-97.7320, 30.2767],
                                [-97.7315, 30.2692],
                            ]
                        ],
                    },
                }
    ],
    "transmission": [
                {
                    "type": "Feature",
                    "properties": {"source": "HIFLD electric power transmission lines"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-97.7421, 30.2722], [-97.7265, 30.2806]],
                    },
                }
    ],
}

# Backward-compatible fixture for direct geometry-engine consumers.
SAMPLE = {
    "parcel": PARCELS["TRAVIS-DEMO-001"],
    "constraints": [
        {
            "id": layer_id,
            "label": layer_id.title(),
            "reason": "Synthetic test fixture",
            "setback_m": 0,
            "features": features,
        }
        for layer_id, features in SOURCE_FEATURES.items()
    ],
}
