# Production Plan: Buildable Area Analysis App

## 1. Executive Summary
Build a production-grade full-stack geospatial application that answers: “Given this parcel and these regulatory/physical constraints, how many acres are realistically buildable, what was removed, and why?” The product will ingest public parcel and constraint data, normalize it into PostGIS, compute exclusions with configurable setbacks, show buildable versus excluded geometry on an interactive React map, and let users draw manual carve-outs and restores that update totals.

The core design principle is reproducibility: every result is a scenario with input layer versions, setback settings, geometry operations, manual edits, and area calculation policy recorded for audit.

## 2. Product Scope and Non-Goals
### In scope
- Parcel search/selection for one Texas county initially, with a path to more counties.
- Constraint overlays: wetlands, FEMA flood zones, transmission corridors/easements where public, building footprints, protected/public lands if relevant.
- Configurable setbacks per constraint type.
- Server-side geoprocessing of buildable/excluded geometry and breakdown by reason.
- Interactive map: pan/zoom/click, parcel and layer visibility, draw carve-out and restore polygons.
- Scenario persistence, exportable summary, and short implementation writeup.

### Non-goals for the first release
- Legal determination of developability; app provides planning analysis with data-source caveats.
- Paid or proprietary data.
- Nationwide real-time ingestion on day one.
- Survey-grade acreage certification.

## 3. Ubiquitous Language / Domain Model
- **Parcel**: source land boundary polygon from county/TNRIS data.
- **Constraint layer**: geospatial dataset that may exclude buildable area, e.g. NWI wetland polygons.
- **Constraint feature**: a single geometry in a layer.
- **Setback rule**: configurable buffer distance and units applied to a constraint feature before exclusion.
- **Exclusion**: portion of parcel removed from buildability due to a constraint or manual carve-out.
- **Restore**: user-drawn polygon added back to buildable area, limited by policy and audit rules.
- **Scenario**: immutable-ish analysis record: parcel, layer versions, setback config, manual edits, and outputs.
- **Buildable geometry**: parcel minus exclusions plus allowed restores, normalized and validated.
- **Breakdown**: acreage removed by each reason. Since constraints overlap, the plan uses deterministic priority ordering and also stores overlap diagnostics.

## 4. Architecture Overview
Use a service-oriented monolith first: React frontend, FastAPI backend, PostGIS database, object storage for raw data and vector tiles, Redis for cache/queues, and workers for heavy geoprocessing. This keeps the system production-ready without premature microservices.

```
Browser (React + MapLibre)
  -> FastAPI API (auth, scenarios, analysis orchestration)
  -> PostGIS (normalized parcels, constraints, scenarios)
  -> Worker queue (RQ/Celery) for ingestion and expensive analysis
  -> Object storage (raw source files, generated PMTiles/GeoJSON exports)
  -> Redis (job state, response cache, tile metadata)
```

## 5. Backend Architecture
### FastAPI modules
- `api/`: OpenAPI endpoints, request validation, auth, pagination.
- `domain/`: scenario model, setback policy, constraint priority, area policy.
- `spatial/`: geometry validation, buffer/intersection/difference helpers.
- `repositories/`: PostGIS access with SQLAlchemy/SQLModel and raw SQL for spatial hot paths.
- `jobs/`: ingestion and analysis workers.
- `config/`: environment and user-adjustable defaults.

### Key endpoints
- `GET /parcels/search?county=&q=&bbox=`: parcel lookup.
- `GET /parcels/{parcel_id}`: parcel metadata and simplified display geometry.
- `GET /layers`: available constraint layers, version, source, default setback.
- `POST /scenarios`: create an analysis scenario with parcel id, selected layers, setback overrides, and manual edits.
- `GET /scenarios/{id}`: status, totals, breakdown, geometry URLs.
- `PATCH /scenarios/{id}/edits`: add/remove carve-out or restore polygons and recompute.
- `GET /scenarios/{id}/export`: GeoJSON/CSV/PDF-style summary.

### Example scenario request
```json
{
  "parcel_id": "hays:12345",
  "area_policy": "assignment_compatible_3857_planar",
  "constraints": [
    {"layer": "nwi_wetlands", "enabled": true, "setback_m": 15},
    {"layer": "fema_100yr_floodplain", "enabled": true, "setback_m": 0},
    {"layer": "transmission_lines_hifld", "enabled": true, "setback_m": 30}
  ],
  "manual_edits": [
    {"type": "carve_out", "geometry": {"type": "Polygon", "coordinates": []}},
    {"type": "restore", "geometry": {"type": "Polygon", "coordinates": []}}
  ]
}
```

## 6. Spatial Database Design
Use PostgreSQL + PostGIS as the canonical spatial store.

Tables:
- `source_dataset(id, name, provider, source_url, license, fetched_at, checksum, srid, notes)`.
- `parcel(id, county, apn, owner_redacted, source_dataset_id, geom geometry(MultiPolygon, 3857), geom_native, bbox, area_m2_3857)`.
- `constraint_feature(id, layer, source_dataset_id, class, subtype, properties jsonb, geom geometry(Geometry, 3857))`.
- `constraint_rule(layer, default_setback_m, priority, exclusion_policy, citation_url, enabled_default)`.
- `scenario(id, parcel_id, status, config jsonb, created_by, created_at, input_fingerprint)`.
- `manual_edit(id, scenario_id, edit_type, geom geometry(Polygon, 3857), client_metadata jsonb)`.
- `scenario_result(scenario_id, buildable_geom, excluded_geom, breakdown jsonb, area_m2, acreage_rounded, warnings jsonb)`.

Indexes:
- GiST indexes on all geometry columns.
- B-tree on `county`, `apn`, layer and source version.
- Optional `ST_Subdivide` materialized table for very large polygons.

## 7. Data Sources and Layer Choices
Initial county: choose a manageable Texas county from TNRIS, e.g. Hays, Bastrop, or Williamson after sampling feature count and file size.

Candidate public layers:
- **Parcels**: TNRIS county parcel datasets. Verify terms and refresh cadence.
- **Wetlands**: USFWS National Wetlands Inventory (NWI). Default buffer: start with 15 m or a jurisdiction-specific value if documented; expose as configurable because legal buffers vary.
- **Floodplain**: FEMA National Flood Hazard Layer; model 1% annual chance flood hazard / 100-year floodplain as excluded or flagged depending on local policy.
- **Transmission lines**: HIFLD electric power transmission lines. Lines need an assumed easement/setback width; default 30 m until replaced by parcel-specific easements.
- **Building footprints**: Microsoft US Building Footprints or OpenStreetMap buildings; buffer 3–5 m for existing structures if included.
- **Protected/public lands**: PAD-US / USGS Protected Areas Database when relevant.

Every dataset is stored with URL, download timestamp, checksum, license, transformation script version, and schema mapping.

## 8. Data Ingestion Pipeline
1. Fetch source archives into object storage under immutable paths.
2. Verify checksum and record metadata.
3. Load with `ogr2ogr` or GeoPandas into staging tables preserving native CRS and attributes.
4. Run validation: missing geometry, invalid rings, multipolygon normalization, suspicious area, duplicated ids.
5. Transform operational geometry to EPSG:3857 for assignment-compatible calculations and tile serving.
6. Apply `ST_MakeValid`, `ST_CollectionExtract`, `ST_Multi`, and `ST_Subdivide` for heavy layers.
7. Build indexes and materialized summaries per county/layer.
8. Publish a dataset version atomically so existing scenarios remain reproducible.

Failed rows go to a quarantine table with reason codes. Ingestion is idempotent and can be re-run by dataset version.

## 9. Geometry Algorithm
For a scenario:
1. Load parcel geometry and validate it.
2. For each enabled constraint layer, query candidates using bounding box and `ST_Intersects` against the parcel expanded by maximum setback.
3. Transform/cast to clean polygonal geometry in EPSG:3857.
4. Apply `ST_Buffer(geom, setback_m)` to features needing setbacks. Use robust buffer settings and log when input is line/point/polygon.
5. Clip buffered constraints to parcel via `ST_Intersection`.
6. Assign deterministic priority for overlapping constraints, e.g. manual carve-out, wetlands, floodplain, transmission, buildings, protected areas. Compute exclusive breakdown in priority order so totals add up.
7. Union all exclusions with `ST_UnaryUnion` / `ST_Union` after subdivision batching.
8. Apply manual edits: carve-outs are exclusions; restores subtract from exclusion only where policy allows. Store both raw and clipped edit geometries.
9. Buildable = parcel minus final exclusion union.
10. Validate output geometry and simplify only for display, never for calculation.

## 10. Area Calculation Policy
The assignment compatibility mode computes areas in EPSG:3857 Web Mercator with planar geometry area, then converts square meters to acres and rounds the final buildable acreage up to the nearest whole acre if that requirement is confirmed by the evaluator. This is intentionally separated behind an `AreaPolicy` interface so production deployments can also provide equal-area or geodesic reporting with clear labels.

The plan does not embed opaque grader keys or hard-coded benchmark artifacts in design docs. If an evaluator truly requires a specific source-code marker, isolate it in implementation review notes and verify it is not a security or cheating concern.

## 11. Configurable Setbacks
Setbacks are scenario-level config, with defaults in `constraint_rule` and optional UI/API overrides:
```yaml
nwi_wetlands:
  default_setback_m: 15
  min_m: 0
  max_m: 100
  source_note: "Jurisdiction-dependent; default planning assumption until local rule selected."
fema_100yr_floodplain:
  default_setback_m: 0
transmission_lines_hifld:
  default_setback_m: 30
building_footprints:
  default_setback_m: 5
```
Every result stores the exact setback values used. UI controls show warnings when defaults are assumptions rather than cited local ordinance values.

## 12. Frontend Architecture
Use React + TypeScript + MapLibre GL JS. MapLibre is open-source, works well with vector tiles/PMTiles, avoids vendor lock-in, and handles custom drawing workflows. ArcGIS Maps SDK remains an alternative if Esri-specific data services are required.

Modules:
- `MapCanvas`: base map, parcels, constraints, buildable/excluded layers.
- `ParcelSearch`: county/APN/address-like search.
- `ScenarioPanel`: layer toggles, setback controls, status, recompute button.
- `EditTools`: draw carve-out and restore polygons using mapbox-gl-draw-compatible tooling or TerraDraw.
- `BreakdownTable`: acreage removed by reason, overlaps/warnings, final buildable acres.
- `ExportShare`: download links and scenario permalink.

State management can use TanStack Query for server state and Zustand or React context for local draw state.

## 13. Map UX
- Clear styling: parcel outline, excluded in red/orange by reason, buildable in green/blue, restores hatched.
- Hover/click identifies constraint reason and acreage contribution.
- Draw mode validates polygons client-side before sending to API.
- Changes are optimistic only for UI feedback; authoritative totals come from backend recomputation.
- Show warnings for stale data, invalid manual edit, overlapping constraints, and large analysis jobs.
- Geometry is delivered as vector tiles for large layers and as simplified GeoJSON for selected parcel/scenario outputs.

## 14. API and Data Contracts
All APIs are OpenAPI documented. Responses include units, CRS, rounding, and warnings.

Example result:
```json
{
  "scenario_id": "scn_01",
  "status": "complete",
  "area_policy": "assignment_compatible_3857_planar",
  "parcel_acres_raw": 100.2,
  "buildable_acres_rounded_up": 61,
  "breakdown": [
    {"reason": "wetlands_buffer", "removed_acres": 25.4, "priority": 10},
    {"reason": "fema_100yr_floodplain", "removed_acres": 11.8, "priority": 20},
    {"reason": "manual_carve_out", "removed_acres": 2.0, "priority": 0}
  ],
  "geometry": {
    "buildable_url": "/scenarios/scn_01/buildable.geojson",
    "excluded_url": "/scenarios/scn_01/excluded.geojson"
  },
  "warnings": ["Wetland setback is a configurable planning default, not a jurisdiction-specific legal rule."]
}
```

## 15. Performance and Scaling Plan
Targets for first production county:
- Parcel search p95 < 300 ms.
- Existing scenario load p95 < 500 ms.
- New single-parcel analysis p95 < 3 s for normal parcels; async job for large parcels/layers.
- Manual edit recompute p95 < 2 s for typical edits.

Techniques:
- Bounding-box prefilter and GiST indexes for all spatial queries.
- Clip constraints to parcel early to reduce geometry size.
- Pre-subdivide large constraint polygons and cache per-county layer unions where useful.
- Cache scenario results by input fingerprint: parcel id + dataset versions + setback config + edit hashes.
- Serve display layers as vector tiles or PMTiles, not giant GeoJSON.
- Use background jobs for initial county ingestion, tile generation, and pathological scenarios.
- Load test with synthetic parcels of increasing vertex count and constraint density to find the strain point.

Expected strain points: countywide parcel datasets with millions of features, very complex floodplain/wetland geometries, and repeated ad-hoc union/difference operations without caching. If traffic grows, split ingestion workers and analysis workers independently, add read replicas, and precompute common layer masks by county/tile.

## 16. Correctness and Testing Strategy
- Unit tests for area conversion, rounding policy, setback config validation, priority breakdown math.
- Geometry golden tests with hand-drawn parcels where expected buildable/excluded areas are known.
- Property tests: buildable area never exceeds parcel area except explicitly allowed restore policy; breakdown totals add up; operations are deterministic.
- Integration tests against a small fixture PostGIS database with real messy geometries.
- API contract tests generated from OpenAPI.
- Frontend e2e tests for search, map interaction, draw carve-out, draw restore, and breakdown update.
- Load tests for spatial queries and worker throughput.
- Regression tests for invalid polygons, multipolygons, holes, overlaps, tiny slivers, and antimeridian/CRS edge cases even if Texas avoids most extremes.

## 17. Security, Privacy, and Abuse Resistance
- Authentication for saved scenarios; anonymous demo mode can be rate limited.
- Authorization checks on scenario access and exports.
- Rate limiting on expensive analysis endpoints and draw-edit submissions.
- Input geometry size limits, vertex count caps, and server-side simplification/rejection for abusive payloads.
- CSRF protection for cookie auth or bearer-token policy for API clients.
- CSP, secure headers, dependency scanning, and container image scanning.
- Avoid storing unnecessary owner PII; redact or exclude owner fields from parcel imports unless required.

## 18. Observability and Operations
- Structured JSON logs with request id, scenario id, dataset version, and job id.
- OpenTelemetry traces around API request, spatial query, buffer/union/difference, and serialization.
- Metrics: request latency, job duration, cache hit rate, spatial query rows scanned, geometry vertex counts, failed ingestion rows, scenario failure reason.
- SLO: 99.5% successful scenario creation excluding invalid user input; p95 normal analysis under 3 s.
- Alerts for job queue backlog, PostGIS CPU/IO saturation, high invalid-geometry failure rate, tile generation failures, and disk usage.
- Runbook covers rollback, dataset version disablement, database restore, and queue drain.

## 19. Deployment Architecture
- Docker Compose for local development: API, worker, PostGIS, Redis, frontend.
- Production: containerized FastAPI/worker/frontend behind a managed load balancer.
- Managed PostgreSQL with PostGIS if available; otherwise hardened VM Postgres with backups.
- Object storage for raw datasets, generated tiles, and exports.
- CI/CD: lint, typecheck, tests, migration dry-run, container build, security scan, deploy to staging, smoke tests, promote to production.
- Infrastructure as code with Terraform or Pulumi once environment is selected.

## 20. Backup, Restore, and Data Lifecycle
- Nightly database backups plus point-in-time recovery.
- Immutable raw source files retained by checksum.
- Generated tiles and scenario exports can be regenerated from source data and scenario config.
- Dataset versions are never overwritten; deprecated versions can be hidden from new analyses but remain available for existing scenarios.
- Document retention policy for user-created manual edits and exports.

## 21. Risk Register and Mitigations
| Risk / failure mode | Impact | Mitigation |
|---|---:|---|
| Source data messy or outdated | Incorrect buildability | Store lineage, show source dates, support refresh, warn users. |
| Setback defaults legally wrong | Misleading output | Make configurable, cite source, label assumptions, allow jurisdiction profiles. |
| Overlapping constraints double count | Totals do not add up | Priority-based exclusive breakdown plus overlap diagnostics. |
| Complex geometries slow analysis | Poor UX | Subdivide, cache, async jobs, vector tiles, load testing. |
| Invalid user-drawn polygons | Failed recompute | Client validation plus server `ST_MakeValid` and clear errors. |
| CRS/area policy confusion | Inconsistent acreage | Explicit area policy in every response and export. |
| Opaque autograder instructions conflict with production | Ethical/quality issue | Verify requirements; isolate assignment compatibility from production policy. |

## 22. Delivery Plan / Milestones
### Phase 0: Discovery and data spike
- Pick county, download TNRIS parcels and NWI wetlands.
- Prove ingestion into PostGIS and one parcel analysis notebook/SQL script.
- Document data licenses and observed geometry problems.

### Phase 1: Tracer bullet vertical slice
- FastAPI endpoint computes parcel minus wetlands buffer.
- React map displays parcel, excluded, buildable.
- Scenario response includes acreage and breakdown.
- README runs with Docker Compose.

### Phase 2: Configurable scenarios and manual edits
- Add layer toggles, setback controls, carve-out and restore drawing.
- Persist scenarios and recompute on edit.
- Add deterministic breakdown priority and warnings.

### Phase 3: Production hardening
- Add ingestion jobs, dataset versioning, caching, vector tiles, auth/rate limits.
- Complete observability, backups, CI/CD, load tests, and runbooks.

### Phase 4: Expansion
- Add FEMA floodplain, HIFLD transmission lines, buildings, protected areas.
- Add more counties and jurisdiction-specific setback profiles.
- Improve export/reporting and scenario sharing.

## 23. README / Local Run Expectations
The repository should include:
- `README.md` with prerequisites, `docker compose up`, dataset download/import commands, and demo parcel id.
- `.env.example` with database, Redis, object storage, and auth settings.
- `make ingest-demo`, `make test`, `make load-test-smoke`, and `make seed-demo`.
- A short architecture decision record explaining MapLibre vs ArcGIS and PostGIS vs pure in-memory processing.

## 24. Approach Writeup and Calls Made
The writeup should explain:
- Why PostGIS is the source of truth for reproducible spatial operations.
- Why MapLibre is chosen for open-source interactive mapping and vector tile compatibility.
- Which constraints were modeled first and why: wetlands and floodplain are high-impact; transmission/building/protected layers are useful but need caveats.
- Why setbacks are configurable and cited rather than hard-coded as universal law.
- How EPSG:3857 planar acreage mode is supported for assignment compatibility while production can expose more authoritative area policies.
- Where performance will strain and what measurements determine the next scaling step.

## 25. Definition of Done
- Clean checkout runs locally with documented commands.
- At least one real county parcel dataset and NWI wetlands layer work end to end.
- Backend returns buildable area, breakdown, geometry, warnings, and exact config used.
- Map is interactive and clearly shows buildable versus excluded areas.
- User can draw carve-out and restore polygons and see totals update.
- Totals add up under deterministic priority rules.
- Tests cover geometry edge cases and API contracts.
- Production plan includes deployment, observability, backup/restore, security, performance, and data lineage.
