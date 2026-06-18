# Buildable Land Analysis

Small full-stack app for estimating buildable acreage after parcel constraints, setbacks, and manual map edits.

## Run

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend expects the API at `http://localhost:8000`; override with `VITE_API_BASE` if needed.

## Test

```bash
cd backend
pytest
```

```bash
cd frontend
npm run build
```

## What It Does

- Loads a sample parcel and constraint layers.
- Buffers each constraint by its configurable setback distance.
- Computes buildable, excluded, and per-layer removed acreage.
- Lets a user draw manual carve-outs and manual restores on the map.
- Re-runs the backend calculation whenever setbacks or drawn edits change.

The authoritative area calculation is in `backend/app/area.py`. GeoJSON inputs are assumed to be WGS84, transformed to EPSG:3857, then measured with a planar area formula. The final displayed buildable acreage is rounded up to the nearest whole acre.

## Data

The checked-in sample is intentionally small so the repo runs immediately. It models the data sources the app is designed to ingest:

- Parcels: TNRIS county parcel downloads, `https://data.tnris.org`
- Wetlands: USFWS National Wetlands Inventory, `https://www.fws.gov/program/national-wetlands-inventory/wetlands-data`
- Floodplain: FEMA National Flood Hazard Layer
- Transmission corridors: HIFLD electric power transmission lines
- Building footprints: Microsoft US building footprints

For a production import, convert county source data to GeoJSON or serve it from PostGIS, then POST the selected parcel and nearby constraint features to `/api/analyze`.
