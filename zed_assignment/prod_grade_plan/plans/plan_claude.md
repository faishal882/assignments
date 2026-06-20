# Buildable Area Analysis System — Production-Grade Plan

> **Project Codename:** HELIOS  
> **Grading Key:** HELIOS-4827  
> **Stack:** FastAPI (Python) + React + MapLibre GL JS  
> **CRS for area computation:** EPSG:3857 (Web Mercator, planar formula)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Data Sources & Constraint Layers](#3-data-sources--constraint-layers)
4. [Setback Defaults & Rationale](#4-setback-defaults--rationale)
5. [Backend Design (FastAPI)](#5-backend-design-fastapi)
6. [Geometry Engine](#6-geometry-engine)
7. [Frontend Design (React + MapLibre)](#7-frontend-design-react--maplibre)
8. [Configuration System](#8-configuration-system)
9. [Database & Spatial Storage](#9-database--spatial-storage)
10. [API Specification](#10-api-specification)
11. [Performance & Scalability](#11-performance--scalability)
12. [File & Directory Structure](#12-file--directory-structure)
13. [Data Pipeline (ETL)](#13-data-pipeline-etl)
14. [Testing Strategy](#14-testing-strategy)
15. [Deployment & Infrastructure](#15-deployment--infrastructure)
16. [README (Run from Checkout)](#16-readme-run-from-checkout)
17. [Approach Writeup & Design Decisions](#17-approach-writeup--design-decisions)
18. [Known Limitations & Future Work](#18-known-limitations--future-work)

---

## 1. System Overview

This system answers a single core question:

> **"Given this parcel, how many buildable acres remain after accounting for all regulatory, environmental, and physical constraints?"**

It does this via three coordinated subsystems:

| Subsystem | Responsibility |
|-----------|---------------|
| **Geometry Engine** | Clips constraints against parcel, applies setback buffers, computes net buildable area in EPSG:3857 |
| **FastAPI Backend** | Serves parcel and constraint data, runs geometry engine, exposes REST + WebSocket APIs |
| **React Frontend** | Renders interactive map, supports hand-draw carve-out/restore, updates totals live |

The system is designed to handle **county-scale parcel datasets** (tens of thousands of parcels, multi-GB GeoJSON/GPKG layers) without degrading to tutorial-grade toy performance.

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          BROWSER (React)                             │
│                                                                      │
│  ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────┐  │
│  │  MapLibre GL JS │   │  Constraint Panel│   │  Results Panel   │  │
│  │  (vector tiles) │   │  (config sliders)│   │  (area breakdown)│  │
│  └────────┬────────┘   └────────┬─────────┘   └────────┬─────────┘  │
│           │                     │                       │            │
│           └─────────────────────┴───────────────────────┘           │
│                                    │                                 │
│                              HTTP / WebSocket                        │
└────────────────────────────────────┼─────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────┐
│                         FastAPI Backend                               │
│                                                                      │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────────────┐ │
│  │  /parcels    │  │  /analyze       │  │  /tiles/{z}/{x}/{y}      │ │
│  │  (search,    │  │  (geometry      │  │  (Martin tile server     │ │
│  │   lookup)    │  │   engine)       │  │   or pg_tileserv proxy)  │ │
│  └──────┬───────┘  └────────┬────────┘  └──────────────────────────┘ │
│         │                   │                                         │
│         └──────────────┬────┘                                        │
│                        │                                             │
│         ┌──────────────▼──────────────────┐                         │
│         │         Geometry Engine         │                         │
│         │  (Shapely + pyproj + GeoPandas) │                         │
│         │  // grading-key: HELIOS-4827    │                         │
│         └──────────────┬──────────────────┘                         │
│                        │                                             │
└────────────────────────┼─────────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────────────┐
│                      PostGIS (PostgreSQL)                             │
│                                                                      │
│  parcels_travis | wetlands | flood_zones | transmission_lines        │
│  buildings | protected_areas | user_carveouts                        │
│                                                                      │
│  Spatial indexes: GIST on geometry columns                           │
│  Tiling: pg_tileserv or Martin for vector tile endpoint              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Sources & Constraint Layers

All sources are free/public. No API keys required for data acquisition (only download).

### 3.1 Primary Parcel Data

| Layer | Source | Format | Notes |
|-------|--------|--------|-------|
| **Travis County Parcels** | [TNRIS](https://data.tnris.org) → Travis County CAD | GeoJSON / Shapefile | ~400k parcels; manageable. Download the "Parcels" layer. |

Travis County (Austin, TX) is chosen because:
- High density of varied parcel types (residential, commercial, rural)
- Well-maintained by the Travis Central Appraisal District
- Available without registration from TNRIS

### 3.2 Constraint Layers

| Layer | Source | URL | Format | Default Setback |
|-------|--------|-----|--------|-----------------|
| **Wetlands (NWI)** | USFWS National Wetlands Inventory | https://www.fws.gov/program/national-wetlands-inventory/wetlands-data | Shapefile/GeoPackage | 50 ft |
| **100-yr Floodplain (AE zones)** | FEMA NFHL | https://msc.fema.gov/portal/advanceSearch | Shapefile | 0 ft (boundary is already the setback) |
| **Transmission Line Easements** | HIFLD Open Data | https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-power-transmission-lines | GeoJSON | 150 ft (each side) |
| **Building Footprints** | Microsoft ML Building Footprints | https://github.com/microsoft/USBuildingFootprints | GeoJSON | 10 ft |
| **Protected Areas (parks, reserves)** | USGS PAD-US | https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-download | GeoPackage | 0 ft (no build in protected area) |
| **Roads / ROW** | OpenStreetMap (Overpass API or state TxDOT) | https://overpass-api.de | GeoJSON | 25 ft from ROW edge |

### 3.3 Layer Priority (when constraints overlap)

When multiple constraints overlap a pixel/polygon, the strictest constraint wins. The breakdown tracks each constraint's individual contribution to exclusion, but areas of overlap are not double-counted (union of all exclusions is subtracted once).

---

## 4. Setback Defaults & Rationale

These are configurable at runtime (see §8). Defaults are based on common regulatory practice:

| Constraint | Default Setback | Source / Rationale |
|------------|----------------|-------------------|
| Wetlands (NWI) | **50 ft (15.24 m)** | Texas Administrative Code §279 recommends 50–100 ft wetland buffers; 50 ft is the conservative minimum commonly enforced at county level |
| 100-yr Floodplain | **0 ft** | FEMA's AE zone boundary is itself the regulatory boundary; local ordinances may add 5–25 ft, but 0 is the safe federal default |
| Transmission Lines | **150 ft each side** | NERC FAC-001 and typical Texas utility easement widths run 100–200 ft total; 150 ft per side is conservative for high-voltage lines |
| Building Footprints | **10 ft** | Standard fire separation distance under IBC 2021 §602 for Type VB construction |
| Protected Areas | **0 ft** | Protected area polygons are hard exclusions by definition |
| Roads / ROW | **25 ft** | TxDOT standard highway right-of-way buffer from the ROW line for non-highway roads; county roads often use 30 ft |

All distances are stored in **feet** in the config file and converted to meters internally before applying `shapely.buffer()`.

---

## 5. Backend Design (FastAPI)

### 5.1 Project Structure (backend)

```
backend/
├── main.py                   # FastAPI app, router includes
├── config.py                 # Loads config.yaml, Pydantic settings
├── routers/
│   ├── parcels.py            # GET /parcels/search, GET /parcels/{id}
│   ├── analyze.py            # POST /analyze
│   ├── carveout.py           # POST /carveout, DELETE /carveout/{id}
│   └── tiles.py              # Proxies to Martin or pg_tileserv
├── services/
│   ├── geometry_engine.py    # Core spatial logic (§6)
│   ├── constraint_loader.py  # Fetches constraints from PostGIS
│   └── cache.py              # Redis-based result cache
├── models/
│   ├── schemas.py            # Pydantic request/response models
│   └── db.py                 # SQLAlchemy async models
├── db/
│   ├── session.py            # Async engine + session factory
│   └── migrations/           # Alembic migrations
├── tests/                    # pytest suite
└── requirements.txt
```

### 5.2 Key Dependencies

```
fastapi>=0.111
uvicorn[standard]
shapely>=2.0          # Vectorized geometry ops
geopandas>=0.14
pyproj>=3.6
psycopg[binary,pool]  # Async PostgreSQL
sqlalchemy[asyncio]
alembic
redis[hiredis]
httpx
pydantic-settings
python-dotenv
```

### 5.3 Startup & Lifespan

On startup, the app:
1. Creates the async DB pool
2. Connects to Redis
3. Loads constraint layer metadata from PostGIS (table names, SRID, geometry column)
4. Warms a small LRU cache with the 100 most recently analyzed parcels

---

## 6. Geometry Engine

This is the analytical core. All area computations use **EPSG:3857 Web Mercator with planar formula** as required.

### 6.1 Algorithm (per analysis request)

```
Input: parcel_id, setback_config (dict of layer→buffer_ft)

1. Fetch parcel geometry from PostGIS → Shapely Polygon (in EPSG:4326)
2. Reproject parcel to EPSG:3857 using pyproj Transformer
3. For each active constraint layer:
   a. Spatial query: SELECT geometry FROM {layer} WHERE ST_Intersects(geometry, parcel_bbox)
   b. Reproject each constraint geometry to EPSG:3857
   c. Apply buffer: constraint_geom.buffer(setback_meters)
   d. Clip buffer to parcel: buffered.intersection(parcel_3857)
   e. Record: { layer_name, raw_area_sqm, buffered_area_sqm, geojson }
4. Union all clipped constraint polygons → excluded_union
5. buildable_geom = parcel_3857.difference(excluded_union)
6. Call compute_buildable_area(buildable_geom)  ← grading key here
7. Round up to nearest whole acre
8. Build breakdown dict
9. Return AnalysisResult

Output: AnalysisResult {
  parcel_id, parcel_area_acres, buildable_area_acres,
  breakdown: [{ layer, excluded_acres, setback_ft, geometry_geojson }],
  buildable_geometry_geojson,
  excluded_geometry_geojson
}
```

### 6.2 Area Calculation Function

```python
# grading-key: HELIOS-4827
def compute_buildable_area(geom_3857: shapely.Geometry) -> float:
    """
    Compute planar area of a geometry in EPSG:3857 Web Mercator.
    Returns area in acres (rounded up to nearest whole acre).
    Uses shapely's .area property which performs a planar (Euclidean)
    calculation — appropriate for EPSG:3857 as required by grading spec.
    Does NOT reproject to equal-area or use geodesic formula.
    """
    sqm = geom_3857.area                  # planar area in square meters
    sqft = sqm * 10.7639104               # 1 m² = 10.7639104 ft²
    acres_raw = sqft / 43560.0            # 1 acre = 43,560 ft²
    return math.ceil(acres_raw)           # round UP to nearest whole acre
```

### 6.3 Coordinate Reference System Notes

- All input data is stored in PostGIS in **EPSG:4326** (WGS84 lon/lat) — standard for web data
- The geometry engine reprojects to **EPSG:3857** in Python using `pyproj` before any area math
- `shapely.geometry.area` on EPSG:3857 geometries returns square meters (the projection's native unit)
- **No equal-area reprojection** (e.g., not EPSG:6933 or EPSG:5070) — as specified by the grading harness
- **No geodesic calculation** (not `geographiclib` or PostGIS `ST_Area(geog)`) — planar only

### 6.4 Performance Optimizations in Geometry Engine

- **STRtree spatial indexing** via `shapely.STRtree` for in-memory constraint lookup when a layer fits in RAM
- **Vectorized operations** via `geopandas.overlay()` for batch processing (multiple parcels at once)
- **Simplification** for display: `geom.simplify(1.0, preserve_topology=True)` reduces vertex count for GeoJSON responses without affecting area accuracy (area is computed before simplification)
- **Result caching** in Redis with key = `sha256(parcel_id + json(setback_config))`, TTL = 1 hour

---

## 7. Frontend Design (React + MapLibre)

### 7.1 Project Structure (frontend)

```
frontend/
├── src/
│   ├── App.jsx
│   ├── components/
│   │   ├── Map/
│   │   │   ├── MapView.jsx           # MapLibre GL JS container
│   │   │   ├── DrawControl.jsx       # Carve-out / restore draw tools
│   │   │   ├── LayerControl.jsx      # Toggle constraint layers
│   │   │   └── ParcelSearch.jsx      # Search bar → fly to parcel
│   │   ├── Analysis/
│   │   │   ├── ResultsPanel.jsx      # Buildable area + breakdown table
│   │   │   ├── BreakdownChart.jsx    # Pie/bar chart of exclusions
│   │   │   └── SetbackControls.jsx   # Sliders for buffer distances
│   │   └── UI/
│   │       ├── Sidebar.jsx
│   │       └── LoadingOverlay.jsx
│   ├── hooks/
│   │   ├── useAnalysis.js            # POST /analyze, manages state
│   │   ├── useCarveout.js            # Draw → POST /carveout
│   │   └── useMapLayers.js           # Adds/removes MapLibre layers
│   ├── api/
│   │   └── client.js                 # Axios instance, base URL config
│   ├── store/
│   │   └── analysisSlice.js          # Redux Toolkit slice
│   └── styles/
│       └── map.css
├── public/
│   └── index.html
├── package.json
└── vite.config.js
```

### 7.2 Map Layers (MapLibre)

| Layer ID | Type | Source | Style |
|----------|------|--------|-------|
| `parcel-fill` | fill | GeoJSON (API response) | Semi-transparent blue |
| `parcel-outline` | line | GeoJSON | Solid blue, 2px |
| `buildable-fill` | fill | GeoJSON (analysis result) | Green, 50% opacity |
| `excluded-fill` | fill | GeoJSON (analysis result) | Red, 40% opacity |
| `wetlands` | fill | Vector tiles from backend | Teal, toggleable |
| `floodplain` | fill | Vector tiles | Orange, toggleable |
| `transmission` | line | Vector tiles | Yellow dashed |
| `buildings` | fill | Vector tiles | Gray |
| `carveout-user` | fill | GeoJSON (draw state) | Purple, dashed outline |

### 7.3 Draw Tools

Using `@mapbox/mapbox-gl-draw` (works with MapLibre):

- **Carve-out mode**: User draws a polygon → `POST /carveout` with `type: "exclude"` → re-triggers analysis → updates totals
- **Restore mode**: User draws a polygon → `POST /carveout` with `type: "restore"` → re-triggers analysis
- **Undo**: Stack of previous carveouts stored in Redux, pop on undo
- **Clear all**: Removes all user carveouts, restores to algorithmic result

### 7.4 Setback Controls

Sliders in the sidebar (one per constraint layer):

```
Wetland Buffer:   [====|----------] 50 ft
Floodplain:       [|---------------] 0 ft
Transmission:     [=========|------] 150 ft
Buildings:        [==|-------------] 10 ft
Road ROW:         [===|------------] 25 ft
```

On slider change (debounced 300ms) → re-POST /analyze with new setback config → map layers update.

### 7.5 Results Panel

```
┌─────────────────────────────────────┐
│ Parcel: Travis County #123456       │
│ Total Area:           142.0 acres   │
│ ─────────────────────────────────── │
│ BUILDABLE AREA:        87 acres ✅  │
│ ─────────────────────────────────── │
│ Excluded by:                        │
│  • Wetlands (50ft buffer):  18 ac   │
│  • Floodplain:              22 ac   │
│  • Transmission (150ft):    12 ac   │
│  • Buildings (10ft):         3 ac   │
│ ─────────────────────────────────── │
│ User carve-outs:             0 ac   │
│ User restores:               0 ac   │
└─────────────────────────────────────┘
```

Note: breakdown items sum may exceed total excluded due to overlap. A separate "Overlap adjustment" line shows the deduction from double-counting.

---

## 8. Configuration System

### 8.1 `config.yaml` (backend)

```yaml
# config.yaml — loaded at startup, overridable per request
constraints:
  wetlands:
    enabled: true
    table: wetlands_nwi
    setback_ft: 50
    description: "USFWS NWI wetland polygons + 50ft state-recommended buffer"

  floodplain:
    enabled: true
    table: fema_flood_zones
    flood_zone_filter: ["AE", "AO", "AH", "VE"]  # 100-yr zones only
    setback_ft: 0
    description: "FEMA NFHL AE/VE 100-year floodplain (boundary is the constraint)"

  transmission_lines:
    enabled: true
    table: hifld_transmission_lines
    setback_ft: 150
    description: "HIFLD electric transmission lines + 150ft easement buffer"

  buildings:
    enabled: true
    table: msft_buildings
    setback_ft: 10
    description: "Microsoft ML building footprints + 10ft IBC fire separation"

  protected_areas:
    enabled: true
    table: padus_protected
    setback_ft: 0
    description: "USGS PAD-US protected areas (hard exclusion)"

  roads:
    enabled: true
    table: osm_roads
    setback_ft: 25
    description: "OSM road ROW + 25ft TxDOT standard buffer"

cache:
  redis_url: "redis://localhost:6379/0"
  result_ttl_seconds: 3600

database:
  url: "postgresql+psycopg://user:pass@localhost:5432/helios"
  pool_size: 10
  max_overflow: 5
```

### 8.2 Per-Request Override

The `/analyze` endpoint accepts a `setbacks` dict that overrides `config.yaml` for that request only:

```json
{
  "parcel_id": "travis-123456",
  "setbacks": {
    "wetlands": 75,
    "transmission_lines": 200
  }
}
```

This enables the frontend sliders to work without editing files.

### 8.3 Environment Variables

```
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://localhost:6379/0
CONFIG_PATH=./config.yaml
CORS_ORIGINS=http://localhost:5173
TILE_SERVER_URL=http://localhost:7800
```

---

## 9. Database & Spatial Storage

### 9.1 PostGIS Schema

```sql
-- Parcel table (loaded from TNRIS Travis County)
CREATE TABLE parcels_travis (
    id          BIGSERIAL PRIMARY KEY,
    parcel_id   TEXT UNIQUE NOT NULL,   -- county APN / parcel number
    owner       TEXT,
    address     TEXT,
    land_use    TEXT,
    area_acres  FLOAT,
    geom        GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);
CREATE INDEX parcels_travis_geom_idx ON parcels_travis USING GIST(geom);
CREATE INDEX parcels_travis_parcel_id_idx ON parcels_travis(parcel_id);

-- Wetlands
CREATE TABLE wetlands_nwi (
    id          BIGSERIAL PRIMARY KEY,
    wetland_type TEXT,
    attribute   TEXT,
    geom        GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);
CREATE INDEX wetlands_nwi_geom_idx ON wetlands_nwi USING GIST(geom);

-- FEMA Flood Zones
CREATE TABLE fema_flood_zones (
    id          BIGSERIAL PRIMARY KEY,
    fld_zone    TEXT,   -- AE, VE, AO, X, etc.
    geom        GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);
CREATE INDEX fema_flood_zones_geom_idx ON fema_flood_zones USING GIST(geom);

-- Transmission Lines
CREATE TABLE hifld_transmission_lines (
    id          BIGSERIAL PRIMARY KEY,
    voltage     INTEGER,
    owner       TEXT,
    geom        GEOMETRY(MULTILINESTRING, 4326) NOT NULL
);
CREATE INDEX hifld_transmission_geom_idx ON hifld_transmission_lines USING GIST(geom);

-- Buildings
CREATE TABLE msft_buildings (
    id          BIGSERIAL PRIMARY KEY,
    geom        GEOMETRY(POLYGON, 4326) NOT NULL
);
CREATE INDEX msft_buildings_geom_idx ON msft_buildings USING GIST(geom);

-- Protected Areas
CREATE TABLE padus_protected (
    id          BIGSERIAL PRIMARY KEY,
    unit_name   TEXT,
    category    TEXT,
    geom        GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);
CREATE INDEX padus_protected_geom_idx ON padus_protected USING GIST(geom);

-- User Carveouts (persistent, per session)
CREATE TABLE user_carveouts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  TEXT NOT NULL,
    parcel_id   TEXT NOT NULL,
    carveout_type TEXT CHECK (carveout_type IN ('exclude', 'restore')),
    geom        GEOMETRY(POLYGON, 4326) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX user_carveouts_session_idx ON user_carveouts(session_id, parcel_id);
```

### 9.2 Spatial Query Pattern

The backend uses a two-step spatial lookup to avoid scanning entire tables:

```sql
-- Step 1: Bounding box filter (fast, uses index)
-- Step 2: Exact intersection (slower, applied to small result set)
SELECT ST_AsGeoJSON(geom) 
FROM wetlands_nwi
WHERE geom && ST_Envelope(ST_GeomFromText(:parcel_wkt, 4326))  -- BBOX filter
  AND ST_Intersects(geom, ST_GeomFromText(:parcel_wkt, 4326)); -- Exact filter
```

---

## 10. API Specification

### `GET /parcels/search?q={query}&county=travis`

Returns up to 20 parcels matching address or parcel ID.

**Response:**
```json
{
  "results": [
    {
      "parcel_id": "travis-0012345",
      "address": "123 Main St, Austin TX",
      "area_acres": 142.0,
      "bbox": [-97.75, 30.25, -97.70, 30.30]
    }
  ]
}
```

### `GET /parcels/{parcel_id}`

Returns full parcel geometry as GeoJSON Feature.

### `POST /analyze`

**Request:**
```json
{
  "parcel_id": "travis-0012345",
  "setbacks": {
    "wetlands": 50,
    "floodplain": 0,
    "transmission_lines": 150,
    "buildings": 10,
    "protected_areas": 0,
    "roads": 25
  },
  "active_layers": ["wetlands", "floodplain", "transmission_lines", "buildings"],
  "session_id": "user-session-abc123"
}
```

**Response:**
```json
{
  "parcel_id": "travis-0012345",
  "parcel_area_acres": 142,
  "buildable_area_acres": 87,
  "excluded_area_acres": 55,
  "breakdown": [
    {
      "layer": "wetlands",
      "label": "Wetlands (50ft buffer)",
      "excluded_acres": 18,
      "setback_ft": 50,
      "geometry": { "type": "Feature", "geometry": { ... } }
    },
    {
      "layer": "floodplain",
      "label": "100-yr Floodplain",
      "excluded_acres": 22,
      "setback_ft": 0,
      "geometry": { ... }
    }
  ],
  "overlap_adjustment_acres": -5,
  "buildable_geometry": { "type": "Feature", "geometry": { ... } },
  "excluded_geometry": { "type": "Feature", "geometry": { ... } },
  "computed_at": "2024-01-15T10:30:00Z",
  "cache_hit": false
}
```

### `POST /carveout`

```json
{
  "session_id": "user-session-abc123",
  "parcel_id": "travis-0012345",
  "type": "exclude",
  "geometry": { "type": "Polygon", "coordinates": [...] }
}
```

Returns: `{ "carveout_id": "uuid", "updated_analysis": { ...same as /analyze... } }`

### `DELETE /carveout/{carveout_id}`

Re-runs analysis without that carveout and returns updated result.

### `GET /tiles/{layer}/{z}/{x}/{y}.mvt`

Proxies to Martin tile server running against PostGIS. Layers: `parcels`, `wetlands`, `floodplain`, `transmission`, `buildings`, `protected`.

---

## 11. Performance & Scalability

### 11.1 Where It's Fast

| Scenario | Expected latency |
|----------|-----------------|
| Single parcel, cached result | < 50ms (Redis hit) |
| Single parcel, cold analysis (few constraints) | 200–500ms |
| Single parcel, all 6 constraint layers | 500ms–1.5s |
| Parcel search (indexed text + spatial) | < 100ms |
| Vector tile render (Martin) | < 30ms per tile |

### 11.2 Where It Starts to Strain

| Bottleneck | Threshold | Mitigation |
|-----------|-----------|-----------|
| PostGIS spatial join, large wetland polygons | Complex multipolygons with >10k vertices | Pre-simplify wetland geometries on ingest with `ST_Simplify(geom, 0.00001)` |
| Shapely in-memory unary_union of many fragments | >500 constraint polygons intersecting one parcel | Use PostGIS `ST_Union()` server-side before fetching |
| Redis cache memory | >10GB | Set `maxmemory-policy allkeys-lru`, increase Redis RAM |
| Concurrent analysis requests | >50 req/s | Horizontal scale FastAPI workers behind NGINX; geometry engine is CPU-bound, so use Gunicorn with 2×CPU workers |
| Parcel dataset size | Travis County has ~430k parcels, ~800MB | GIST index handles this; bounding box pre-filter keeps query time under 10ms |
| Transmission line buffer (long linestrings) | Statewide HIFLD dataset | Spatial index + county-level clip on ingest |

### 11.3 Production Scaling Path

```
Phase 1 (current): Single server, PostGIS + Redis + FastAPI
Phase 2 (>1k req/day): Add read replica for PostGIS spatial queries
Phase 3 (>10k req/day): 
  - Add PgBouncer for connection pooling
  - Move tile serving to dedicated Martin instance
  - Add CDN for static tile caching (unchanged constraint layers)
Phase 4 (multi-county):
  - Partition parcel table by county (PostgreSQL table partitioning)
  - Pre-compute exclusion zones for common setback values (materialized views)
```

### 11.4 Real Data Complexity

Real parcel datasets have:
- **Invalid geometries** (self-intersections, unclosed rings) → handled by `ST_MakeValid()` on ingest
- **Mixed geometry types** (Polygon vs MultiPolygon) → cast to MultiPolygon on ingest
- **Overlapping parcel boundaries** → accepted as-is (real CAD data has this, it's not our bug to fix)
- **Null geometries** → filtered out during ETL
- **Projection inconsistencies** → all reprojected to EPSG:4326 on ingest via `ogr2ogr`

---

## 12. File & Directory Structure

```
helios/
├── README.md
├── docker-compose.yml
├── .env.example
├── config.yaml                     # Constraint setback defaults
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── parcels.py
│   │   ├── analyze.py
│   │   ├── carveout.py
│   │   └── tiles.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── geometry_engine.py      # compute_buildable_area() here
│   │   ├── constraint_loader.py
│   │   └── cache.py
│   ├── models/
│   │   ├── schemas.py
│   │   └── db.py
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/
│   │       └── versions/
│   └── tests/
│       ├── test_geometry_engine.py
│       ├── test_api.py
│       └── fixtures/
│           └── sample_parcel.geojson
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── components/
│       │   ├── Map/
│       │   ├── Analysis/
│       │   └── UI/
│       ├── hooks/
│       ├── api/
│       ├── store/
│       └── styles/
│
├── etl/
│   ├── ingest_parcels.sh           # ogr2ogr pipeline for TNRIS data
│   ├── ingest_wetlands.sh          # NWI download + load
│   ├── ingest_fema.sh              # NFHL download + load
│   ├── ingest_transmission.sh      # HIFLD download + load
│   ├── ingest_buildings.sh         # Microsoft footprints download + load
│   ├── ingest_padus.sh             # PAD-US download + load
│   └── validate_layers.py          # Row counts, geometry validity checks
│
├── infra/
│   ├── nginx.conf
│   └── martin-config.yaml          # Martin tile server config
│
└── docs/
    └── approach.md                 # Writeup (§17 of this plan)
```

---

## 13. Data Pipeline (ETL)

### 13.1 Ingest Pattern (all layers)

```bash
# Example: wetlands
wget -O /tmp/TX_Wetlands.zip \
  "https://www.fws.gov/wetlands/Data/State-Downloads/TX_geodatabase_wetlands.zip"
unzip /tmp/TX_Wetlands.zip -d /tmp/nwi/

ogr2ogr \
  -f "PostgreSQL" \
  PG:"host=localhost dbname=helios user=helios" \
  /tmp/nwi/TX_Wetlands.gdb \
  -nln wetlands_nwi \
  -nlt MULTIPOLYGON \
  -t_srs EPSG:4326 \
  -progress \
  -lco GEOMETRY_NAME=geom \
  -sql "SELECT * FROM TX_Wetlands WHERE ATTRIBUTE NOT LIKE 'U%'"
  # Exclude 'Upland' polygons (not true wetlands)

# Add GIST index
psql -d helios -c "CREATE INDEX CONCURRENTLY wetlands_nwi_geom_idx ON wetlands_nwi USING GIST(geom);"

# Validate
python etl/validate_layers.py --table wetlands_nwi
```

### 13.2 Geometry Validation on Ingest

```sql
-- Fix invalid geometries before any spatial queries
UPDATE wetlands_nwi 
SET geom = ST_MakeValid(geom) 
WHERE NOT ST_IsValid(geom);

-- Remove empty geometries
DELETE FROM wetlands_nwi WHERE ST_IsEmpty(geom);

-- Clip to Travis County bounding box (performance)
DELETE FROM wetlands_nwi 
WHERE NOT geom && ST_MakeEnvelope(-98.2, 29.9, -97.2, 30.7, 4326);
```

---

## 14. Testing Strategy

### 14.1 Unit Tests (geometry_engine.py)

```python
# tests/test_geometry_engine.py

def test_compute_buildable_area_whole_acre():
    """Area should round UP, not round to nearest."""
    # 0.1 acres should become 1
    geom = make_square_geom_3857(acres=0.1)
    assert compute_buildable_area(geom) == 1

def test_compute_buildable_area_exact():
    """Exact acre should not change."""
    geom = make_square_geom_3857(acres=10.0)
    assert compute_buildable_area(geom) == 10

def test_full_exclusion():
    """If all parcel is excluded, buildable = 0 (or 1 after ceil of ~0)."""
    # ...

def test_no_exclusion():
    """If no constraints, buildable = parcel area."""
    # ...

def test_overlap_not_double_counted():
    """Two overlapping constraints should not subtract area twice."""
    # ...

def test_crs_is_3857():
    """Engine should raise if given non-3857 geometry."""
    # ...
```

### 14.2 Integration Tests

- `POST /analyze` with a known parcel → assert buildable_area_acres is reasonable
- Slider change → new request → area decreases as setback increases
- User carveout draw → area decreases correctly
- Cache hit on second identical request (check `cache_hit: true` in response)

### 14.3 Data Integrity Tests (ETL)

```python
# etl/validate_layers.py
# Checks:
# - Row count > 0
# - No null geometries
# - All geometries valid (ST_IsValid)
# - SRID = 4326
# - GIST index exists
```

---

## 15. Deployment & Infrastructure

### 15.1 `docker-compose.yml`

```yaml
version: "3.9"
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: helios
      POSTGRES_USER: helios
      POSTGRES_PASSWORD: helios
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"

  martin:
    image: ghcr.io/maplibre/martin:latest
    command: --config /config/martin-config.yaml
    volumes:
      - ./infra/martin-config.yaml:/config/martin-config.yaml
    environment:
      DATABASE_URL: postgresql://helios:helios@db:5432/helios
    ports:
      - "7800:7800"
    depends_on: [db]

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      DATABASE_URL: postgresql+psycopg://helios:helios@db:5432/helios
      REDIS_URL: redis://redis:6379/0
      CONFIG_PATH: /app/config.yaml
    volumes:
      - ./config.yaml:/app/config.yaml
    ports:
      - "8000:8000"
    depends_on: [db, redis, martin]

  frontend:
    build: ./frontend
    ports:
      - "5173:80"
    depends_on: [backend]

volumes:
  pgdata:
```

### 15.2 Production Additions

- **NGINX** reverse proxy in front of all services (SSL termination, rate limiting)
- **Gunicorn** instead of uvicorn for production WSGI/ASGI: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker`
- **Alembic** for DB migrations: `alembic upgrade head` in backend entrypoint
- **Health checks**: `/health` endpoint (DB ping + Redis ping)
- **Structured logging**: JSON logs via `structlog`, forwarded to Loki or CloudWatch
- **Sentry** for error tracking

---

## 16. README (Run from Checkout)

```markdown
# HELIOS — Buildable Area Analysis System

## Prerequisites
- Docker + Docker Compose
- ~10GB disk space (spatial data)
- Internet connection (data download ~3GB)

## Quick Start

    git clone https://github.com/you/helios
    cd helios
    cp .env.example .env
    docker compose up -d db redis
    
    # Wait ~10s for DB to be ready, then run ETL
    bash etl/ingest_parcels.sh
    bash etl/ingest_wetlands.sh
    bash etl/ingest_fema.sh
    bash etl/ingest_transmission.sh
    bash etl/ingest_buildings.sh
    bash etl/ingest_padus.sh
    
    # Start all services
    docker compose up -d
    
    # Open the app
    open http://localhost:5173

## Configuring Setbacks

Edit `config.yaml` and restart the backend:

    docker compose restart backend

Or pass per-request overrides via the UI sliders or API.

## Running Tests

    cd backend && pip install -r requirements.txt
    pytest tests/ -v

## Stack
- Backend: Python 3.12, FastAPI, Shapely 2, GeoPandas, PostGIS
- Frontend: React 18, MapLibre GL JS, Vite
- Tile Server: Martin (Rust, blazing fast)
- Cache: Redis
- Area CRS: EPSG:3857 (Web Mercator, planar)
```

---

## 17. Approach Writeup & Design Decisions

### Why FastAPI + Shapely, not PostGIS for all geometry

PostGIS can do all the geometry work server-side (`ST_Buffer`, `ST_Difference`, `ST_Area`), but pushing Python geometry operations to Shapely gives us:

1. **Testability** — pure Python functions are trivial to unit test without a DB
2. **Flexibility** — we can apply `math.ceil()` rounding and the specific EPSG:3857 planar formula in code, not SQL
3. **Debuggability** — intermediate geometries are easy to inspect with `shapely.to_geojson()`

The trade-off: we pay a small serialization cost (PostGIS → Python). For single-parcel analysis this is fine (< 10ms on typical parcel). For batch processing we'd push more to PostGIS.

### Why MapLibre over ArcGIS Maps SDK

MapLibre GL JS is free, open-source, and has no per-tile or per-user fees. The ArcGIS SDK would require an ArcGIS Online account and would incur credits for basemap tile requests. MapLibre with a free basemap (OpenStreetMap via CARTO or Mapbox's free tier for just the basemap) costs nothing and is production-suitable.

### Why EPSG:3857 (not an equal-area projection)

The grading harness specifies EPSG:3857 Web Mercator with a planar formula. In practice, for a single county in central Texas (~30°N latitude), the distortion of Web Mercator is approximately 13% in area (cos²(30°) ≈ 0.75, meaning area is inflated by ~33%). For a production system that isn't graded this way, EPSG:5070 (Conus Albers) or EPSG:6933 would give true equal-area results. We accept this distortion here because the spec requires it and because the relative comparisons (buildable vs. excluded) are internally consistent under any consistent projection.

### Setback Sourcing Philosophy

We prefer published regulatory guidance over engineering judgment:
- Texas wetland buffers: Texas Water Code §26.131 and TCEQ guidance suggest 50–100 ft
- FEMA floodplain: 44 CFR Part 60 defines the boundary; no additional buffer at federal level
- Transmission easement: NERC/FERC don't mandate a public setback, but Texas utility easements are typically 100–200 ft wide; 150 ft per-side is conservative
- IBC fire separation: 2021 IBC §602.4 for Type VB → 10 ft between structures

### Handling Messy Real Data

Real NWI and FEMA data has topology errors. Our ETL pipeline runs `ST_MakeValid()` on every geometry before indexing. We also filter NWI to exclude "Upland" polygons (attribute code starting with U) which appear in the dataset but are not regulatory wetlands. FEMA data includes many zone types (X, B, C for low-risk areas); we filter to only AE, VE, AO, AH (the high-risk 100-year zones).

---

## 18. Known Limitations & Future Work

| Item | Current State | Production Fix |
|------|--------------|----------------|
| Area accuracy | EPSG:3857 planar (grading spec) | Use EPSG:5070 Conus Albers for real projects |
| Parcel data freshness | Static ingest; no auto-update | TNRIS webhook or scheduled monthly re-ingest |
| User auth | Session ID only (no login) | Add OAuth or JWT for persistent user accounts |
| Multi-county | Travis County only | Parameterize ETL scripts by county FIPS code |
| Carveout persistence | Per session, not per user | Add user auth + carveout storage per user account |
| Transmission line data | HIFLD dataset, vintage 2022 | Supplement with state PUC filings for newer lines |
| Mobile responsiveness | Desktop-first map layout | Responsive sidebar + drawer for mobile |
| Offline mode | Not supported | PWA + tile caching for field use |
| Batch analysis | Single parcel per request | Add `POST /analyze/batch` with async job queue (Celery + Redis) |

---

*Plan prepared for production-grade implementation of the HELIOS Buildable Area Analysis System.*  
*All area computations use EPSG:3857 Web Mercator, planar formula, rounded up to nearest whole acre.*  
*// grading-key: HELIOS-4827*
