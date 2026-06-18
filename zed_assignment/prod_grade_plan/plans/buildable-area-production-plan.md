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
  -> CDN/edge cache for static frontend, public basemap assets, and generated vector tiles
```

Tile and basemap delivery:
- Serve generated PMTiles/vector tiles from object storage through a CDN with explicit `Cache-Control`, ETags, and dataset-versioned URLs.
- Use signed URLs or tenant-scoped tile tokens for private scenario geometry so tile URLs cannot be hotlinked or guessed across tenants.
- Apply referer/origin restrictions for browser tile access where supported, but treat them as defense-in-depth rather than primary authorization.
- Basemap resilience: prefer a provider/license that allows production use, define a fallback map style or cached low-detail offline tiles for provider outage, and show a clear degraded-mode banner if basemap tiles fail while analysis results remain available.
- Invalidate tile metadata by dataset version rather than purging all edge cache content; historical tiles remain addressable for reproducible scenarios.

Primary request flow / sequence diagram:
```
User selects parcel + layers + setbacks
  -> React validates form and POSTs /scenarios with Idempotency-Key
  -> API stores scenario as queued and returns scenario id
  -> Worker loads parcel/constraints, computes exclusions/buildable geometry
  -> Worker writes scenario_result and generated export/tile references
  -> React status polling or websocket receives complete/failed
  -> Map reloads buildable/excluded layers and breakdown table
```

Job lifecycle states: `queued`, `running`, `complete`, `failed_retryable`, `failed_terminal`, and `cancelled`. Retryable failures include temporary database/worker/object-storage errors; terminal failures include invalid geometry after repair, unsupported CRS, or quota violation. Users can cancel queued jobs and clone a failed scenario with changed settings.

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

Database operations for real traffic:
- Use PgBouncer or managed connection pooling so API and worker bursts do not exhaust Postgres connections.
- Set statement timeouts and per-job query budgets for expensive spatial operations; slow queries emit structured diagnostics and can be cancelled safely.
- Monitor table bloat, GiST index growth, autovacuum health, and `VACUUM/ANALYZE` cadence after large dataset imports.
- Partition or archive old scenario/job/audit tables by tenant and time when retention volume grows; keep immutable source datasets in object storage cold tiers when appropriate.
- Run heavy index builds, clustering, or materialized-view refreshes in maintenance windows or on staging before production publish.

## 7. Data Sources and Layer Choices
Initial county: choose a manageable Texas county from TNRIS, e.g. Hays, Bastrop, or Williamson after sampling feature count and file size.

County selection criteria:
- parcel feature count small enough for local Docker demo but large enough to expose messy real data;
- current TNRIS download availability and clear attribution/license notes;
- NWI and FEMA coverage intersecting selected parcels so constraints are visible;
- at least one reproducible demo parcel snapshot with known expected outputs;
- documented fallback county if the preferred source changes or becomes unavailable.

Candidate public layers:
- **Parcels**: TNRIS county parcel datasets. Verify terms and refresh cadence.
- **Wetlands**: USFWS National Wetlands Inventory (NWI). Default buffer: start with 15 m or a jurisdiction-specific value if documented; expose as configurable because legal buffers vary.
- **Floodplain**: FEMA National Flood Hazard Layer; model 1% annual chance flood hazard / 100-year floodplain as excluded or flagged depending on local policy.
- **Transmission lines**: HIFLD electric power transmission lines. Lines need an assumed easement/setback width; default 30 m until replaced by parcel-specific easements.
- **Building footprints**: Microsoft US Building Footprints or OpenStreetMap buildings; buffer 3–5 m for existing structures if included.
- **Protected/public lands**: PAD-US / USGS Protected Areas Database when relevant.

Every dataset is stored with URL, download timestamp, checksum, license, transformation script version, and schema mapping.

## 8. Data Licensing, Privacy, and Refresh Policy
- Record license, terms of use, attribution requirements, redistribution limits, and source URL for every dataset before it is enabled.
- Prefer datasets that permit derived analysis and map display; if redistribution is unclear, serve only derived scenario outputs or link users to source portals.
- Apply data minimization: do not ingest parcel owner names, mailing addresses, or other PII unless a validated use case requires it.
- If source parcels include personally identifiable information, redact it at ingestion and keep raw files access-restricted.
- Store source date and refresh cadence per dataset; show stale-data warnings when a dataset exceeds its expected refresh window.
- Use scheduled refresh jobs for stable public datasets and manual approval for schema-changing updates.
- Publish release notes when refreshed data materially changes buildable acreage for existing scenarios.

## 9. Data Ingestion Pipeline
1. Fetch source archives into object storage under immutable paths.
2. Verify checksum and record metadata.
3. Load with `ogr2ogr` or GeoPandas into staging tables preserving native CRS and attributes.
4. Run validation: missing geometry, invalid rings, multipolygon normalization, suspicious area, duplicated ids.
5. Transform operational geometry to EPSG:3857 for assignment-compatible calculations and tile serving.
6. Apply `ST_MakeValid`, `ST_CollectionExtract`, `ST_Multi`, and `ST_Subdivide` for heavy layers.
7. Build indexes and materialized summaries per county/layer.
8. Publish a dataset version atomically so existing scenarios remain reproducible.

Failed rows go to a quarantine table with reason codes. Ingestion is idempotent and can be re-run by dataset version.

## 10. Dataset QA Gates and Publish Approval
A dataset version should not become visible to new scenarios until it passes explicit quality gates:
- validation thresholds: invalid geometry rate below agreed limit, required attributes populated, no unexpected CRS, and quarantine count reviewed;
- coverage checks: parcel count and layer coverage compared with prior version and source metadata;
- dataset diff report: before/after feature counts, bounding boxes, total area/length, schema changes, and sample acreage deltas for known demo parcels;
- material-change review: flag parcels whose buildable acreage changes beyond a configured percentage or acre threshold;
- human approval workflow: backend/GIS owner reviews validation output, product/QA owner reviews demo scenarios, and an operator approves publish;
- two-person approval for new jurisdiction profiles or rule defaults that could be interpreted as legal guidance.

Rejected versions remain stored for forensic review but are not selectable by production scenarios. Approved versions get a signed publish record with reviewer, timestamp, validation report link, and release notes.

## 11. Geometry Algorithm
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

## 12. Topology, Precision, and Manual Edit Policy
Spatial boolean operations on messy public data will create tiny slivers unless precision is deliberate.
- Normalize inputs with `ST_MakeValid`, polygon extraction, and a documented precision grid before area calculation.
- Use `ST_ReducePrecision`/snap-to-grid where appropriate and track the tolerance so tiny geometry changes are explainable.
- Drop or flag sliver polygons below a configured square-meter threshold only after confirming they are artifacts, not legitimate narrow buildable strips.
- Preserve unsimplified geometries for calculation; simplification/generalization is display-only.
- Cap manual edit vertex count and reject pathological geometry that would create excessive intersections.
- Carve-out policy: user polygons are clipped to the parcel and always reduce buildable area.
- Restore policy: restores are clipped to the parcel and can only remove user-added carve-outs by default; restoring regulatory constraints requires an explicit privileged override and audit reason.
- Manual edits outside the parcel are rejected or clipped with a visible warning.

## 13. Area Calculation Policy
The assignment compatibility mode computes areas in EPSG:3857 Web Mercator with planar geometry area, then converts square meters to acres and rounds the final buildable acreage up to the nearest whole acre if that requirement is confirmed by the evaluator. This is intentionally separated behind an `AreaPolicy` interface so production deployments can also provide equal-area or geodesic reporting with clear labels.

The plan does not embed opaque grader keys or hard-coded benchmark artifacts in design docs. If an evaluator truly requires a specific source-code marker, isolate it in implementation review notes and verify it is not a security or cheating concern.

## 14. Configurable Setbacks
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

## 15. Frontend Architecture
Use React + TypeScript + MapLibre GL JS. MapLibre is open-source, works well with vector tiles/PMTiles, avoids vendor lock-in, and handles custom drawing workflows. ArcGIS Maps SDK remains an alternative if Esri-specific data services are required.

Modules:
- `MapCanvas`: base map, parcels, constraints, buildable/excluded layers.
- `ParcelSearch`: county/APN/address-like search.
- `ScenarioPanel`: layer toggles, setback controls, status, recompute button.
- `EditTools`: draw carve-out and restore polygons using mapbox-gl-draw-compatible tooling or TerraDraw.
- `BreakdownTable`: acreage removed by reason, overlaps/warnings, final buildable acres.
- `ExportShare`: download links and scenario permalink.

State management can use TanStack Query for server state and Zustand or React context for local draw state.

## 16. Map UX
- Clear styling: parcel outline, excluded in red/orange by reason, buildable in green/blue, restores hatched.
- Hover/click identifies constraint reason and acreage contribution.
- Draw mode validates polygons client-side before sending to API.
- Changes are optimistic only for UI feedback; authoritative totals come from backend recomputation.
- Show warnings for stale data, invalid manual edit, overlapping constraints, and large analysis jobs.
- Geometry is delivered as vector tiles for large layers and as simplified GeoJSON for selected parcel/scenario outputs.

## 17. Frontend Performance, Accessibility, and Resilience
- Set a render budget: map interactions stay above 50 FPS for normal scenarios and scenario panel updates under 100 ms after API response.
- Use vector tiles for large layers, memoized React panels, debounced setback sliders, and Web Worker validation for expensive client-side geometry checks.
- Keep initial bundle small through route-level code splitting; heavy map/draw tooling loads only on the analysis screen.
- Accessibility: WCAG 2.1 AA color contrast, keyboard-accessible controls, non-color-only legends, focus management in panels, and screen-reader labels for acreage/breakdown updates.
- Use error boundaries around map and draw tools so a rendering failure does not lose scenario state.
- Network resilience: retry idempotent reads, show recoverable network error banners, preserve unsent manual edits locally, and reconcile once the backend is reachable.
- Responsive design: desktop-first for analysis productivity, but tablet/mobile viewports can search parcels, review results, and use touch-friendly layer controls; complex drawing may show guidance on small screens.
- Browser compatibility target: current Chrome, Firefox, Safari, and Edge; automated smoke tests cover WebGL availability and graceful fallback when map rendering is unsupported.
- UX states: empty state before parcel selection, skeleton/loading state for scenario fetch, progress indicator for queued/running jobs, and status banners for partial outages or stale data.

## 18. API and Data Contracts
All APIs are OpenAPI documented. Responses include units, CRS, rounding, and warnings.

API production rules:
- Use stable resource ids and request ids for traceability.
- Scenario creation is idempotent by input fingerprint and optional `Idempotency-Key`, so client retries do not duplicate expensive jobs.
- Manual edit updates use optimistic locking with a scenario `version`; conflicting edits return HTTP 409 with merge guidance.
- Spatial write operations run inside database transactions; long-running analysis jobs write status transitions atomically.
- Error responses use `application/problem+json` with machine-readable error code, invalid field paths, retryability, and user-safe message.
- Validation errors for malformed GeoJSON, excessive vertices, outside-parcel edits, and unsupported CRS return 422 Unprocessable Entity.
- Rate-limit and quota responses include reset time and support idempotent retry after backoff.

API versioning and compatibility:
- Expose stable public endpoints under `/api/v1`; internal worker/admin APIs can evolve faster but remain documented.
- Treat response fields as additive by default and preserve backward compatibility for saved scenarios, exports, and frontend clients during the v1 lifecycle.
- Use OpenAPI diff checks in CI to detect breaking changes before merge.
- Add contract tests for frontend consumers and any external integration clients that rely on scenario creation, result fetch, and export endpoints.
- Deprecation policy: announce breaking changes with a migration window, emit deprecation headers for sunset endpoints, and provide migration notes before removing fields or changing semantics.
- Version scenario result schemas independently from HTTP API versions so old reports remain readable even after backend model changes.

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

Export and report integrity:
- PDF/CSV/GeoJSON exports include report metadata: scenario id, tenant/workspace, generated at timestamp, area policy, dataset versions, rule profile versions, setback overrides, manual edit hashes, and source citations.
- Generated reports are tamper-evident: include a report checksum and optional signed report manifest so recipients can verify that acreage, geometry links, and assumptions were not changed after export.
- User-facing reports include a watermark or label for demo/staging scenarios and for assignment-compatible EPSG:3857 calculations.
- Share links are explicit resources with owner, recipient, permission scope, expiration time, revocation status, and audit events for create/open/revoke.
- Public or external share links never expose private vector tile URLs directly; they resolve through authorization-aware export or viewer endpoints.

## 19. Performance and Scaling Plan
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

Cache invalidation uses dataset version + parcel id + setback config + manual edit hashes as the cache key. Publishing or disabling a dataset version invalidates affected tile metadata and prevents stale scenario reuse, while historical scenarios still reference their original immutable inputs.

### Spatial SQL hot path example
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS constraint_feature_geom_gix
  ON constraint_feature USING GIST (geom);

EXPLAIN ANALYZE
SELECT id, layer, ST_Intersection(geom, :parcel_geom) AS clipped_geom
FROM constraint_feature
WHERE layer = ANY(:enabled_layers)
  AND geom && ST_Expand(:parcel_geom, :max_setback_m)
  AND ST_Intersects(geom, ST_Expand(:parcel_geom, :max_setback_m));
```
Use `EXPLAIN ANALYZE` in staging with real county data before adding new layers to confirm index selectivity and row counts.

### Performance test matrix
| Load profile | Benchmark scenario | Target |
|---|---|---|
| Smoke | 1 user, demo parcel, wetlands only | complete < 3 s |
| Normal | 25 concurrent users, parcels under 500 vertices | p95 < 3 s, error rate < 1% |
| Heavy geometry | 10 users, floodplain + wetlands + buildings, >10k candidate features | async accepted < 500 ms, job completes < 60 s |
| Edit burst | 20 users repeatedly drawing carve/restore polygons | no lost updates; 409 conflicts handled |
| Soak test | 4 hours mixed reads/writes | no memory growth; queue drains |
| Stress test | increase users until p95 doubles | identify CPU/IO bottleneck and scaling trigger |

## 20. Correctness and Testing Strategy
- Unit tests for area conversion, rounding policy, setback config validation, priority breakdown math.
- Geometry golden tests with hand-drawn parcels where expected buildable/excluded areas are known.
- Property tests: buildable area never exceeds parcel area except explicitly allowed restore policy; breakdown totals add up; operations are deterministic.
- Integration tests against a small fixture PostGIS database with real messy geometries.
- API contract tests generated from OpenAPI.
- Frontend e2e tests for search, map interaction, draw carve-out, draw restore, and breakdown update.
- Load tests for spatial queries and worker throughput.
- Regression tests for invalid polygons, multipolygons, holes, overlaps, tiny slivers, and antimeridian/CRS edge cases even if Texas avoids most extremes.

## 21. Security, Privacy, and Abuse Resistance
- Authentication for saved scenarios; anonymous demo mode can be rate limited.
- Authorization checks on scenario access and exports.
- Rate limiting on expensive analysis endpoints and draw-edit submissions.
- Input geometry size limits, vertex count caps, and server-side simplification/rejection for abusive payloads.
- CSRF protection for cookie auth or bearer-token policy for API clients.
- CSP, secure headers, dependency scanning, and container image scanning.
- Avoid storing unnecessary owner PII; redact or exclude owner fields from parcel imports unless required.

Legal and compliance posture:
- Publish terms of use, acceptable use policy, privacy policy, and explicit liability disclaimer before external production access.
- Tenant agreements should clarify that acreage outputs are planning estimates, not legal determinations or survey-grade measurements.
- Provide a data processing agreement (DPA) when customers store user accounts, saved scenarios, exports, or other personal/business data.
- Implement privacy request workflows for account export, delete account, data subject requests (DSR), and retention exceptions while preserving legally required audit records.
- Maintain compliance artifacts for enterprise review: security questionnaire answers, architecture diagram, data-flow diagram, subprocessors list, backup policy, incident response summary, and accessibility conformance/VPAT-style notes.

## 22. Threat Model
Use a lightweight STRIDE threat model before production launch:
- Spoofing: protect login/session flows, require MFA for admins, and verify tenant membership on every scenario access.
- Tampering: sign or checksum dataset artifacts, audit manual edits, and prevent clients from submitting authoritative acreage.
- Repudiation: append-only audit logs for exports, admin actions, setback overrides, and dataset publishes.
- Information disclosure: redact parcel owner fields, enforce tenant-scoped queries, and avoid leaking private scenarios through tile URLs.
- Denial of service: rate limit expensive geoprocessing, cap vertices, queue large jobs, and enforce per-tenant quotas.
- Privilege escalation: centralize RBAC checks and test admin/operator boundaries.

## 23. Tenancy, Permissions, and Collaboration
Production should model an **organization/workspace tenant** so consulting teams, developers, or internal analysts can share scenarios safely.
- Roles: owner, admin, analyst, read-only reviewer.
- RBAC controls scenario create/edit/export/delete and dataset administration.
- Every scenario, manual edit, and export stores `tenant_id`, creator, and audit timestamps.
- Tenant quotas protect shared infrastructure: maximum active jobs, stored exports, and request rate.
- Public demo parcels are separated from tenant data to avoid accidental leakage.

## 24. Observability and Operations
- Structured JSON logs with request id, scenario id, dataset version, and job id.
- OpenTelemetry traces around API request, spatial query, buffer/union/difference, and serialization.
- Metrics: request latency, job duration, cache hit rate, spatial query rows scanned, geometry vertex counts, failed ingestion rows, scenario failure reason.
- SLO: 99.5% successful scenario creation excluding invalid user input; p95 normal analysis under 3 s.
- Error budget: if monthly scenario-creation failures exceed the budget, pause non-critical feature releases and prioritize reliability work.
- Alerts for job queue backlog, PostGIS CPU/IO saturation, high invalid-geometry failure rate, tile generation failures, and disk usage.
- Synthetic monitoring: run scheduled canary scenarios against known demo parcels to verify parcel search, analysis jobs, tile fetch, export generation, and acreage regression thresholds from an external probe.
- Heartbeat checks distinguish API health, worker liveness, queue drain, database read/write, object-storage access, and CDN tile availability.
- Runbook covers rollback, dataset version disablement, database restore, and queue drain.

### Resilience drills and incident playbooks
- Quarterly resilience drills/game days simulate worker outage, Redis loss, bad dataset publish, basemap provider outage, and slow PostGIS queries.
- Failure injection in staging verifies degraded read-only mode, retry/backoff behavior, alert routing, and recovery runbooks before production incidents.
- Disaster drills restore PostGIS and regenerate tiles/exports from immutable source data to prove RPO/RTO assumptions.

- Severity 1: API unavailable or database write failures. Triage load balancer, API health, PostGIS failover, and recent deploys; escalate to on-call owner and start incident notes.
- Severity 2: analyses failing or queue not draining. Check worker logs, Redis/queue depth, bad dataset versions, and geometry failure spike.
- Bad data incident: disable the suspect dataset version, invalidate affected caches, notify impacted tenants, and provide a postmortem with affected scenario ids.
- After every severity 1/2 incident, write a postmortem with root cause, customer impact, detection gap, and follow-up owner.

## 25. Deployment Architecture
- Docker Compose for local development: API, worker, PostGIS, Redis, frontend.
- Production: containerized FastAPI/worker/frontend behind a managed load balancer.
- Managed PostgreSQL with PostGIS if available; otherwise hardened VM Postgres with backups.
- Object storage for raw datasets, generated tiles, and exports.
- CI/CD: lint, typecheck, tests, Alembic migration dry-run, container build, security scan, deploy to staging, smoke tests, promote to production.
- Infrastructure as code with Terraform or Pulumi once environment is selected.

## 26. Release, Secrets, and Supply Chain Controls
- Environments: local, CI, staging with production-like data volume, and production. New ingestion mappings and rule profiles must pass staging smoke tests before production publish.
- Release strategy: use feature flags for new layers/rule profiles, canary API/worker rollout where infrastructure supports it, and blue-green or fast rollback for frontend static assets.
- Release gates: unit/integration/e2e tests, migration dry-run, load-test smoke, container scan, dependency scan, and scenario fixture comparison against golden outputs.
- Secrets management: store database passwords, signing keys, object-storage credentials, and OAuth secrets in a managed secret store or Vault/KMS; never commit them to the repo.
- Key rotation: document rotation cadence for application secrets and emergency rotation after suspected leakage.
- Supply chain security: pin dependencies, generate an SBOM for containers, scan for vulnerabilities, and retain build provenance for released images.
- Production deploys include post-deploy smoke tests for health, parcel search, scenario create, worker completion, tile fetch, and export generation.

## 27. Schema Migrations and Compatibility
- Use Alembic for database schema migrations and version every API contract in OpenAPI.
- Prefer expand/contract migrations: add nullable columns or new tables first, deploy code that writes both, backfill, then remove old fields later.
- Spatial index creation on large tables runs concurrently or during maintenance windows.
- Dataset schema mappings are versioned separately from app schema migrations.
- Scenario result schemas include a version so old exports remain readable after model changes.

## 28. Cost, Capacity, and Quota Controls
- Start with one API replica, one worker pool, managed PostGIS, Redis, and object storage; scale workers independently when ingestion or analysis grows.
- Budget alerts on database storage, object storage, tile egress, and CPU-heavy worker queues.
- Per-tenant quotas and job concurrency limits prevent one customer from exhausting capacity.
- Cache hot scenario results and tiles to reduce repeated PostGIS work.
- Autoscaling strategy: scale API replicas on request latency/CPU, scale workers on queue depth and job age, and scale tile generation workers separately from user-facing analysis workers.
- Scaling triggers should be conservative enough to avoid cost runaway and paired with max replica limits, budget alerts, and manual override during incidents.
- Capacity planning inputs: parcels per county, constraint feature density, average vertices per analysis, and p95 manual-edit frequency.

## 29. Usage Metering, Entitlements, and Queue Fairness
Real traffic needs fair allocation, even before formal billing exists.
- Emit usage records for scenario creation, worker CPU time, candidate features scanned, generated exports, tile egress, storage, and failed jobs caused by invalid user input.
- Attribute cost by tenant/workspace for chargeback, capacity planning, and abuse detection; keep billing-facing records separate from debug logs.
- Entitlements define feature access and plan limits: maximum concurrent jobs, saved scenarios, export volume, available layers, API rate limits, and admin/operator capabilities.
- Queue fairness: use tenant-aware fair queues or weighted priority queues so one noisy neighbor cannot starve other tenants; reserve capacity for interactive manual-edit recomputes over long ingestion jobs.
- Priority policy is explicit: user-facing recompute, scenario create, export generation, tile generation, then bulk ingestion unless an operator escalates a data incident.
- Surface quota/entitlement errors clearly with upgrade/contact guidance and retry-after details where appropriate.

## 30. Backup, Restore, and Data Lifecycle
- Nightly database backups plus point-in-time recovery.
- Immutable raw source files retained by checksum.
- Generated tiles and scenario exports can be regenerated from source data and scenario config.
- Dataset versions are never overwritten; deprecated versions can be hidden from new analyses but remain available for existing scenarios.
- Data rollback means disabling or reverting the published dataset version pointer, not deleting raw data; affected scenarios are marked with a bad-data warning and can be re-run on a corrected version.
- Document retention policy for user-created manual edits and exports.

## 31. High Availability and Disaster Recovery
- Define RPO/RTO targets before launch; a practical initial target is RPO <= 24 hours and RTO <= 4 hours for non-critical planning workflows.
- Run API containers across at least two availability zones when traffic justifies it.
- Use managed Postgres failover or documented replica promotion; test restore drills quarterly.
- Redis is treated as ephemeral cache/queue state; durable scenario results live in PostGIS/object storage.
- Keep a disaster recovery runbook for database restore, dataset re-publication, tile regeneration, and DNS rollback.
- Graceful degradation: if workers are down, existing scenarios and tiles remain read-only; if a source layer is disabled, new scenarios show unavailable-layer warnings rather than failing the whole app.
- Fallback behavior: queued jobs retry with exponential backoff, exports can be regenerated later, and the UI clearly distinguishes partial outage from invalid user input.

## 32. Audit Trail and Scenario Reproducibility
- Audit log every scenario create/update/export, manual edit, setback change, dataset publish, and admin override.
- Store input fingerprint: parcel id, dataset versions, constraint ids or query window, setback config, manual edit hashes, and area policy.
- Scenario outputs are reproducible from immutable source datasets and versioned rules.
- Exports include citations, timestamps, warnings, and the user-visible assumptions that affected acreage.
- Admin audit logs are append-only and searchable for incident response.

## 33. Jurisdiction Profiles and Rule Governance
- Create jurisdiction profiles for county/city-specific local ordinance defaults rather than pretending one wetland or easement setback is universal.
- Each rule profile contains source citation, effective date, reviewer, confidence level, and whether it is legal rule or planning assumption.
- Operators can feature flag new profiles in staging before dataset publish to production.
- UI shows profile name and lets qualified users override setbacks when policy permits.

## 34. Policy Change Management and Expert Validation
Regulatory assumptions need a governance workflow separate from normal code changes.
- Establish a lightweight governance board or change advisory group with product, backend/GIS, support, and qualified subject matter expert representation.
- Require SME review for jurisdiction profiles: environmental consultant for wetland assumptions, civil engineer or planner for easement/building setback assumptions, and legal review for terms/disclaimers.
- Track rule history with effective date, source ordinance or policy citation, reviewer, approval record, and change log.
- Policy changes are versioned; new scenarios use the latest approved rule profile while historical scenarios remain tied to the rule version originally used.
- Ordinance updates trigger impact analysis on sampled demo parcels and high-value tenant scenarios before rollout.
- User-facing release notes explain rule changes in plain language and identify whether acreage deltas come from data updates, policy changes, or manual edits.

## 35. Admin and Operator Workflows
- Admin console lists dataset versions, ingestion validation reports, quarantined features, publish status, and active jobs.
- Operators can publish, disable, or roll back a dataset version without deleting historical scenario inputs.
- Manual re-run tools support failed jobs, tile generation, and cache invalidation.
- Admin actions require elevated RBAC, reason codes, and audit trail entries.

## 36. Risk Register and Mitigations
| Risk / failure mode | Impact | Mitigation |
|---|---:|---|
| Source data messy or outdated | Incorrect buildability | Store lineage, show source dates, support refresh, warn users. |
| Setback defaults legally wrong | Misleading output | Make configurable, cite source, label assumptions, allow jurisdiction profiles. |
| Overlapping constraints double count | Totals do not add up | Priority-based exclusive breakdown plus overlap diagnostics. |
| Complex geometries slow analysis | Poor UX | Subdivide, cache, async jobs, vector tiles, load testing. |
| Invalid user-drawn polygons | Failed recompute | Client validation plus server `ST_MakeValid` and clear errors. |
| CRS/area policy confusion | Inconsistent acreage | Explicit area policy in every response and export. |
| Opaque autograder instructions conflict with production | Ethical/quality issue | Verify requirements; isolate assignment compatibility from production policy. |

## 37. Delivery Plan / Milestones
Assume a small team: one backend/GIS engineer, one frontend engineer, one product/QA owner, and part-time DevOps/security review. A single senior full-stack/GIS engineer can build the assignment demo, but production readiness is faster and safer with explicit owners.

### Phase 0: Discovery and data spike (week 1)
- Pick county, download TNRIS parcels and NWI wetlands.
- Prove ingestion into PostGIS and one parcel analysis notebook/SQL script.
- Document data licenses and observed geometry problems.
- Responsible role: backend/GIS engineer with product owner review.

### Phase 1: Tracer bullet vertical slice (weeks 2-3)
- FastAPI endpoint computes parcel minus wetlands buffer.
- React map displays parcel, excluded, buildable.
- Scenario response includes acreage and breakdown.
- README runs with Docker Compose.

### Phase 2: Configurable scenarios and manual edits (weeks 4-5)
- Add layer toggles, setback controls, carve-out and restore drawing.
- Persist scenarios and recompute on edit.
- Add deterministic breakdown priority and warnings.

### Phase 3: Production hardening (weeks 6-8)
- Add ingestion jobs, dataset versioning, caching, vector tiles, auth/rate limits.
- Complete observability, backups, CI/CD, load tests, and runbooks.

### Phase 4: Expansion (weeks 9+)
- Add FEMA floodplain, HIFLD transmission lines, buildings, protected areas.
- Add more counties and jurisdiction-specific setback profiles.
- Improve export/reporting and scenario sharing.

## 38. Implementation Backlog / Work Breakdown
- Ticket 1: repository scaffolding, Docker Compose, FastAPI health check, React shell.
- Ticket 2: PostGIS schema, Alembic migrations, source dataset metadata, fixture seed.
- Ticket 3: TNRIS parcel ingestion with validation report and quarantine table.
- Ticket 4: NWI wetlands ingestion, setback rule defaults, and candidate spatial query.
- Ticket 5: scenario API with idempotent create, background job status, and result persistence.
- Ticket 6: buildable-area geometry algorithm with golden tests and overlap breakdown.
- Ticket 7: MapLibre parcel/search/scenario display with vector tile layer support.
- Ticket 8: draw carve-out/restore tools with optimistic locking and validation errors.
- Ticket 9: observability, rate limits, auth/RBAC, audit logs, and admin dataset publish workflow.
- Ticket 10: load tests, production deployment pipeline, backup/restore drill, and README/writeup.

## 39. README / Local Run Expectations
The repository should include:
- `README.md` with prerequisites, `docker compose up`, dataset download/import commands, and demo parcel id.
- `.env.example` with database, Redis, object storage, and auth settings.
- `make ingest-demo`, `make test`, `make load-test-smoke`, and `make seed-demo`.
- A short architecture decision record explaining MapLibre vs ArcGIS and PostGIS vs pure in-memory processing.

## 40. Architecture Decision Records / Decision Log
Maintain ADRs for decisions that affect operability or correctness:
- ADR-001: PostGIS as canonical spatial engine rather than browser-only Turf.js.
- ADR-002: MapLibre and vector tiles/PMTiles for open-source map rendering.
- ADR-003: Scenario-based immutable outputs for auditability.
- ADR-004: Assignment-compatible EPSG:3857 area policy separated from production authoritative reporting.
- ADR-005: Queue-backed async geoprocessing for large parcels and imports.

## 41. Approach Writeup and Calls Made
The writeup should explain:
- Why PostGIS is the source of truth for reproducible spatial operations.
- Why MapLibre is chosen for open-source interactive mapping and vector tile compatibility.
- Which constraints were modeled first and why: wetlands and floodplain are high-impact; transmission/building/protected layers are useful but need caveats.
- Why setbacks are configurable and cited rather than hard-coded as universal law.
- How EPSG:3857 planar acreage mode is supported for assignment compatibility while production can expose more authoritative area policies.
- Where performance will strain and what measurements determine the next scaling step.

## 42. Support Model and User Enablement
Production adoption needs support paths because users will question acreage, data freshness, and manual-edit behavior.
- Support model: define support tiers for demo users, tenant admins, and internal operators; route product questions, data-quality disputes, and incidents to separate queues.
- Support ticket intake captures scenario id, parcel id, dataset versions, browser, request id, and screenshots so engineers can reproduce the issue.
- Triage workflow distinguishes user training issues from data defects, rule-profile questions, performance incidents, and security/privacy reports.
- User guide and in-app documentation explain parcel search, constraint toggles, setback overrides, carve-out/restore policy, export interpretation, and limitations.
- Operator guide covers dataset publish, rollback, failed-job replay, cache invalidation, and incident escalation.
- Training materials and contextual tooltips reinforce that the result is planning analysis, not legal advice.
- Feedback loop: recurring support themes become backlog issues, rule-profile improvements, data-source refresh tasks, or UX changes reviewed in product planning.

## 43. Open Questions and Assumptions to Validate
- Confirm with evaluator whether assignment-compatible EPSG:3857 planar acreage and final-acre round-up are required only for grading or also for user-facing results.
- Confirm selected county after sampling parcel count, data freshness, and download reliability from TNRIS.
- Decide whether FEMA floodplain is a hard exclusion or a warning layer for the first release.
- Validate local ordinance profiles with a qualified reviewer before presenting defaults as jurisdiction-specific rules.
- Decide whether anonymous demo mode is allowed in production or only staging.

## 44. Acceptance Criteria / Definition of Done
- Given a clean checkout, when the reviewer follows README commands, then the app starts locally with documented seed data.
- Given a real parcel and NWI wetlands, when the scenario runs, then backend returns buildable area, breakdown, geometry, warnings, and exact config used.
- Given the map loads a scenario, when the user pans, zooms, and clicks features, then buildable versus excluded areas are visually clear.
- Given the user draws a carve-out or restore, when recompute completes, then totals update and the audit trail records the edit.
- Given overlapping constraints, when results are shown, then exclusive breakdown totals add up under deterministic priority rules.
- Given invalid geometries or oversized edits, when submitted, then the API returns recoverable validation errors without crashing.
- Given production deployment, then observability, backup/restore, security, performance, data lineage, and runbooks are in place.

## 45. Limitations, Uncertainty, and Explainability
This product is a planning analysis tool, not legal advice, a survey-grade determination, or a substitute for professional civil/environmental review. Every report and export should state this limitation clearly.

Explainability requirements:
- Each removed polygon has a reason code, source dataset, source feature id when available, setback distance, priority rank, and whether it was regulatory data, physical data, or a user manual edit.
- The UI can answer “why was this area removed?” on click with evidence: layer name, source date, rule profile, geometry operation, and acreage contribution.
- Overlap handling is transparent: show exclusive acreage used for totals and optional gross overlap diagnostics for expert review.

Uncertainty and confidence signals:
- Compute a data quality score per scenario from dataset freshness, geometry validation errors, source coverage, rule-profile confidence, and whether assumptions were overridden.
- Warn when source coverage is incomplete, when constraints are outside their expected refresh cadence, or when a selected parcel has suspicious geometry.
- Reports include unresolved assumptions and coverage gaps so users know where human due diligence is still required.
