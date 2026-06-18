SAMPLE = {
    "parcel": {
        "type": "Feature",
        "properties": {
            "name": "Sample Travis County-style parcel",
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
    },
    "constraints": [
        {
            "id": "wetlands",
            "label": "NWI wetlands",
            "reason": "Wetlands and a default 30 m review buffer.",
            "setback_m": 30,
            "features": [
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
        },
        {
            "id": "floodplain",
            "label": "FEMA 100-year floodplain",
            "reason": "Modeled as flood-prone land with no extra default setback.",
            "setback_m": 0,
            "features": [
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
        },
        {
            "id": "buildings",
            "label": "Existing buildings",
            "reason": "Existing structures with a 10 m construction clearance.",
            "setback_m": 10,
            "features": [
                {
                    "type": "Feature",
                    "properties": {"source": "Microsoft US building footprints"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-97.7412, 30.2790],
                                [-97.7399, 30.2790],
                                [-97.7399, 30.2801],
                                [-97.7412, 30.2801],
                                [-97.7412, 30.2790],
                            ]
                        ],
                    },
                }
            ],
        },
        {
            "id": "transmission",
            "label": "Transmission easement",
            "reason": "Transmission corridor using a 30 m easement half-width.",
            "setback_m": 30,
            "features": [
                {
                    "type": "Feature",
                    "properties": {"source": "HIFLD electric power transmission lines"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-97.7421, 30.2722], [-97.7265, 30.2806]],
                    },
                }
            ],
        },
    ],
}
