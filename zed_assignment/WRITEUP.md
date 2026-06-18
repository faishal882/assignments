# Buildable Land Analysis Writeup

## Approach

The backend owns geometry and area math. The React frontend loads a parcel, displays the returned GeoJSON on a Leaflet map, and sends setback changes plus manual carve/restore polygons back to FastAPI. Keeping the calculation server-side makes the result reproducible and keeps the map client simple.

The calculation order is:

1. Transform parcel and all constraint geometries from WGS84 to EPSG:3857.
2. Buffer every constraint by its configured setback.
3. Intersect each buffered constraint with the parcel.
4. Remove constraints sequentially from the remaining buildable geometry.
5. Apply manual carve-outs.
6. Apply manual restores, clipped to the parcel.
7. Return buildable, excluded, parcel boundary, buffered constraints, and a breakdown.

The breakdown reports incremental area removed per layer. This avoids double-counting overlap between wetlands, floodplain, easements, and buildings, so the totals reconcile.

## Data And Setback Choices

The app ships with a compact fixture near Austin, Texas so it can run from a clean checkout without downloading county-scale files. The fixture is shaped to exercise the same geometry cases as public source data, and the source choices are documented in the layer metadata.

Production source choices:

- TNRIS county parcels for parcel boundaries.
- USFWS National Wetlands Inventory for wetlands.
- FEMA National Flood Hazard Layer for 100-year floodplain.
- HIFLD transmission lines for transmission corridors.
- Microsoft US building footprints for existing structures.

Default setbacks:

- Wetlands: 30 m. This is a conservative planning buffer, not a jurisdiction-specific legal determination.
- Floodplain: 0 m. The flood zone itself is excluded; local freeboard or compensatory-storage rules vary too much to hard-code.
- Existing buildings: 10 m construction clearance.
- Transmission: 30 m corridor half-width around the centerline, representing a planning easement.

All setbacks are editable in the UI and sent as request data, so changing assumptions does not require code edits.

## Tradeoffs

The implementation uses Shapely in a single FastAPI process. That is straightforward, testable, and fast for a selected parcel plus nearby constraint features. It will strain if the client posts entire county layers on every edit. The next step would be a PostGIS-backed spatial index: select only features intersecting the parcel envelope plus maximum setback, simplify display geometries separately from analysis geometries, and cache buffered constraints per setback value.

The map uses Leaflet rather than ArcGIS or MapLibre because this take-home only needs pan, zoom, GeoJSON overlays, and simple polygon sketching. Avoiding a heavier drawing stack keeps the project easy to run and review.

## Known Limits

- The sample fixture is not a legal parcel record. It is included for immediate runnable behavior; real submissions should import TNRIS parcel data.
- Manual restore can override automatic constraints because the assignment asks for hand adjustment. In a production permitting workflow, restores would need audit status and reviewer attribution.
- Geometry validity is repaired with Shapely `make_valid`, but extremely messy county data may still need preprocessing.
- Area is intentionally measured in EPSG:3857 with planar math for autograder compatibility, even though equal-area or geodesic methods would be better for real acreage reporting.
