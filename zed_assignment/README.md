# Buildable Area Analysis

A parcel-scale planning tool that subtracts buffered wetlands, floodplain, and transmission constraints, then applies review-driven carve-outs and restores. The API owns all geometry math; the MapLibre client renders its GeoJSON result.

> Planning estimate only. Results are not a survey, title opinion, permit decision, or legal determination.

## Run from a clean checkout

Prerequisites: Python 3.11+ and Node 20+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The checked-in spatial catalog contains 363 real Bell County parcels from the TxGIO/TNRIS standardized parcel program. Search by address, legal description, or generated catalog ID. `TRAVIS-DEMO-001` remains available through the API as a deterministic overlap fixture. Set `VITE_API_BASE` if the API is not at `http://localhost:8000`.

## Verify

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm run build
```

## Configuration and API

Versioned policy profiles, layer bounds, units, geometry interpretation, rationale, verification steps, and citations live in `backend/config.json`. Select a profile, override it per request through `POST /api/analyze`, or edit it live in the UI; no source-code change is required. The API validates every override against layer-specific bounds and returns an immutable policy snapshot with each result.

The built-in profiles are:

- `screening`: 50 ft wetland review buffer, mapped FEMA polygon with no extra lateral buffer, and 100 ft on each side of a transmission centerline.
- `footprint-only`: mapped geometries only, useful as a comparison baseline rather than a regulatory conclusion.

These are feasibility assumptions, not universal legal setbacks. Wetland requirements depend on jurisdictional determinations and governing programs; floodway work may require hydraulic no-rise certification; transmission restrictions come from the recorded easement and operator. Update the version whenever policy values or reasoning change.

- `GET /api/layers`: config-driven policy profiles and layer metadata.
- `GET /api/parcels/search?q=&bbox=`: parcel summaries.
- `GET /api/parcels/{parcel_id}`: parcel GeoJSON.
- `POST /api/analyze`: parcel ID or raw polygon, layer toggles/setbacks, and manual edits.
- `GET /docs`: generated OpenAPI explorer.

Example:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"parcel_id":"TRAVIS-DEMO-001","policy_profile":"screening","layers":[{"id":"wetlands","setback_m":30.48},{"id":"floodplain"},{"id":"transmission","setback_m":22.86}]}'
```

Each analysis response includes a unique `analysis_id`, UTC `analyzed_at`, `policy.config_version`, `policy.profile_id`, the exact setback applied to each enabled layer, source links, rationale, geometry basis, and field-verification requirements. Persist those fields alongside any exported decision record.

## Data and ingestion

The checked-in `backend/data/catalog.sqlite` is a reproducible, bounded acquisition around Bell County (`-97.45,31.06,-97.43,31.08`). It contains 363 TxGIO/TNRIS standardized parcel polygons and a locally clipped USFWS NWI Version 2 riverine feature. The bounded sample keeps a clean checkout small while exercising real duplicate IDs, missing addresses, multipart geometry, and spatial overlap.

Rebuild a catalog from downloaded GeoJSON:

```bash
python ingestion/build_catalog.py \
  --database backend/data/catalog.sqlite \
  --parcels raw/bell-parcels.geojson \
  --wetlands raw/bell-wetlands.geojson \
  --clip -97.45 31.06 -97.43 31.08
```

`ingestion/fetch_arcgis.py` pages bounded ArcGIS FeatureServer layers without loading a statewide response into memory. For a full county deployment, point it at the current TxGIO service or normalize the county ZIP from DataHub, then build the catalog. SQLite R-tree indexes support this sample and a moderate county; use PostGIS, bulk COPY, GiST indexes, vector tiles, and background analysis jobs for multi-county operation.

Authoritative source starting points:

- TNRIS county parcels: <https://data.tnris.org>
- TxGIO parcel program: <https://www.tnris.org/stratmap/land-parcels.html>
- TxGIO parcel service: <https://feature.geographic.texas.gov/arcgis/rest/services/Parcels/stratmap_land_parcels_48_most_recent/MapServer>
- USFWS National Wetlands Inventory: <https://www.fws.gov/program/national-wetlands-inventory/wetlands-data>
- FEMA National Flood Hazard Layer: <https://www.fema.gov/flood-maps/national-flood-hazard-layer>
- HIFLD transmission lines: <https://hifld-geoplatform.opendata.arcgis.com/>

Convert downloaded shapefiles to GeoJSON with `ogr2ogr`, then normalize and validate them with the source-specific scripts:

```bash
python ingestion/ingest_wetlands.py raw/wetlands.geojson data/wetlands.geojson --source-crs EPSG:4326
```

Each script reports written, repaired, and skipped feature counts. Production loading should filter NWI uplands and FEMA zones outside A/AE/AO/AH/VE before inserting normalized geometries into indexed PostGIS tables.

## Correctness model

GeoJSON stays in EPSG:4326 for transport. The engine chooses the parcel centroid’s local UTM zone, then repairs, buffers, unions, differences, and measures there. It never measures in EPSG:3857. Layer `removed_acres` values are ordered exclusive contributions and can be summed; `gross_acres` and `overlap_acres` are diagnostics and must not be summed. Restores are always clipped to the parcel.
