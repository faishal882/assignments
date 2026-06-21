# Buildable Area Analysis - Engineering Writeup

## Purpose and product boundary

The application answers an early feasibility question: given a parcel and a set of mapped constraints, how much land remains potentially buildable? It is a screening tool, not a survey, title opinion, wetland delineation, floodplain permit decision, or legal determination. Its output is useful for comparing parcels and identifying follow-up work; it is not sufficient for final design or acquisition.

The implemented workflow is deliberately parcel-scoped:

1. Find a parcel from the checked-in catalog.
2. Select a policy profile or override individual constraint setbacks.
3. Retrieve only constraint features whose bounding boxes could affect that parcel.
4. Repair, project, buffer, clip, union, and measure those geometries on the backend.
5. Return the buildable geometry, excluded geometry, reconciled acreage, per-layer attribution, and the exact policy assumptions used.
6. Let the reviewer draw carve-outs or restores and recompute the same analysis.

This scope keeps the result explainable and interactive. Authentication, collaborative review, project portfolios, permitting workflow, legal certification, and nationwide data lifecycle management are intentionally outside the take-home.

## Architecture and approach

### Backend as the geometry authority

FastAPI owns geometry validation, policy validation, spatial querying, buffering, overlay operations, acreage, and overlap attribution. The React client never calculates authoritative area. This avoids two geometry implementations producing slightly different totals and gives every UI interaction the same auditable API path.

Input and output GeoJSON use WGS84 (`EPSG:4326`) for interoperability. For each analysis, the backend chooses the WGS84 UTM zone containing the parcel centroid, transforms the parcel and constraints into that metric CRS, and performs all distance and area operations there. Acreage is calculated from projected square metres and rounded to two decimal places only at the API boundary. The full-precision values are retained while reconciling totals.

Local UTM was chosen because the application is parcel-scale and setbacks are expressed in metres or feet. Web Mercator is convenient for map display but distorts distance and area; measuring in it would make acreage latitude-dependent. A statewide batch system would need a documented projection strategy for parcels crossing UTM boundaries, but that edge case is not material for the bounded Bell County sample.

### Geometry pipeline

For every request the engine:

1. Parses the parcel and repairs invalid geometry with Shapely `make_valid`.
2. Retains polygonal output from geometry collections and rejects an empty or non-polygonal parcel.
3. Selects a local UTM CRS from the parcel centroid and projects all candidate geometry.
4. Unions source features within each layer, applies the configured metric buffer, and clips the result to the parcel.
5. Attributes each layer against the union of earlier layers so overlap is not counted twice.
6. Unions all automatic exclusions once and differences that union from the parcel once.
7. Applies manual carve-outs only to land that is still buildable.
8. Applies manual restores only inside the original parcel boundary.
9. Calculates acreage from full-precision geometry, then creates a topology-preserving simplified copy for transport and rendering.

The ordered breakdown has three distinct numbers:

- `removed_acres`: the layer's exclusive incremental contribution. These values reconcile with the excluded total, subject to the displayed 0.01-acre rounding.
- `gross_acres`: the full clipped footprint for that layer before overlap attribution.
- `overlap_acres`: the part already attributed to an earlier layer.

Layer order therefore affects attribution, but not final buildable acreage. The configured order is wetlands, floodplain, then transmission. That rule is deterministic and exposed through the response rather than hidden in the UI. Manual restores use a negative `removed_acres` because they reduce the excluded total.

### Repository and ingestion

The runnable application uses a checked-in SQLite catalog so a clean checkout is deterministic and does not depend on third-party services. SQLite R-tree tables index parcel and constraint bounding boxes. The repository first performs an expanded bounding-box query, then the geometry engine performs exact projected intersection. A layer with no candidates skips projection, buffering, and union work.

Ingestion normalizes source geometry to WGS84, repairs malformed features, clips data to a named county or acquisition region, and records source metadata. It stores two geometry representations:

- Full precision for analysis and acreage.
- Topology-preserving simplified geometry for parcel outlines and map previews.

This avoids repeatedly searching statewide files and avoids sending analysis-grade vertex counts to the browser. The repository interface is intentionally narrow - parcel search, parcel lookup, layer metadata, and parcel-scoped constraints - so it can be replaced by PostGIS without changing the geometry engine or API contract.

### Frontend and interaction model

React owns scenario state while MapLibre renders API-provided GeoJSON. The UI starts with a featured parcel, loads its inexpensive simplified outline first, requests enabled layer previews concurrently, and then replaces those previews with the reconciled final result. Existing MapLibre sources are updated with `setData` rather than removed and recreated.

Setback input values update immediately, while analysis requests are debounced. Superseded requests are aborted so a slower response cannot overwrite a newer scenario. The previous buildable boundary remains briefly as a ghost outline to make geometric change visible. Per-layer loading, empty, and error states distinguish "no intersecting data" from a failed request.

Manual carve-outs and restores are optimistic on the map, but the backend remains authoritative. Restore geometry is clipped to the parcel even if a drawn polygon crosses the boundary. Undo, redo, deletion, keyboard cancellation, unit display, shareable scenario URLs, and PNG export support repeated review rather than a one-shot demonstration.

## Data choices and provenance

### What is included in the runnable sample

The checked-in `backend/data/catalog.sqlite` is a bounded acquisition window around Bell County, Texas (`-97.45,31.06,-97.43,31.08`). It contains:

- 363 real parcel polygons from the TxGIO/TNRIS standardized parcel program.
- One locally clipped USFWS National Wetlands Inventory Version 2 riverine feature.
- Metadata identifying the featured parcel and source datasets.

The small window keeps the repository practical while retaining real-data problems such as duplicate appraisal identifiers, missing addresses, multipart geometry, and irregular boundaries. Stable parcel IDs combine county FIPS, property ID, and source object ID where necessary. Missing addresses fall back to available descriptions.

The code and policy configuration also support FEMA flood hazard polygons and HIFLD transmission lines, but those source layers are not populated in this bounded checked-in catalog. Their empty states are intentional and visible. A production deployment must ingest current local extracts before treating those checks as complete. A separate Travis County fixture remains for deterministic overlap and topology tests.

### Parcels

**Source:** [Texas Geographic Information Office land parcel program](https://www.tnris.org/stratmap/land-parcels.html), with downloads available through the [TxGIO DataHub](https://data.geographic.texas.gov/) and a statewide [parcel map service](https://feature.geographic.texas.gov/arcgis/rest/services/Parcels/stratmap_land_parcels_48_most_recent/MapServer).

TxGIO translates county appraisal district data into a common schema. This is appropriate for parcel discovery and preliminary overlay because it is public, statewide, and standardized. TxGIO also states that source refresh schedules vary and that the geometry is not survey grade. Production use must preserve source vintage, compare it with the appraisal district's current record, and use a boundary survey for legal reliance.

### Wetlands

**Source:** [USFWS National Wetlands Inventory](https://www.fws.gov/program/national-wetlands-inventory/wetlands-data).

NWI is a nationally available mapped wetland and deepwater inventory with downloadable data and web services. It is suitable for early screening, but a mapped NWI boundary is not a current field delineation or jurisdictional determination.

**Default setback:** 50 ft (15.24 m) outward from the mapped polygon edge.

This is a conservative project assumption, not a federal requirement. [Clean Water Act Section 404](https://www.epa.gov/cwa-404/clean-water-laws-regulations-and-executive-orders-related-section-404) regulates certain discharges of dredged or fill material into waters of the United States, including wetlands; it does not establish one universal 50 ft setback. State, local, permit-specific, or project-specific requirements may be smaller, larger, or expressed differently. Before design, obtain a current delineation and jurisdictional review and apply the governing ordinance or permit condition.

### Flood hazard

**Source:** [FEMA National Flood Hazard Layer](https://www.fema.gov/flood-maps/national-flood-hazard-layer).

The intended production filter is the effective 1% annual-chance hazard area, including applicable A, AE, AO, AH, and VE zones, with floodway status retained separately where available.

**Default setback:** 0 ft beyond the mapped polygon.

The mapped hazard footprint itself is excluded for screening. Adding an arbitrary horizontal buffer would imply a regulation that may not exist. Floodway encroachment can require hydraulic analysis, while freeboard is a vertical elevation requirement and cannot be represented by a planar buffer. Before design, confirm the effective FIRM and Flood Insurance Study, zone and floodway status, base flood elevation, local ordinance, and requirements with the local floodplain administrator.

### Transmission corridors

**Source:** [HIFLD Open Data](https://hifld-geoplatform.opendata.arcgis.com/) electric power transmission lines.

The public layer is useful for identifying a possible corridor, but a centerline is not the recorded easement boundary and may not encode voltage, structure type, or operator restrictions reliably enough for final design.

**Default setback:** 100 ft (30.48 m) on each side of the mapped centerline, producing a 200 ft total planning corridor.

[FERC's transmission permitting guidance](https://www.ferc.gov/electric-transmission-facilities-permit-process) says that 100-200 ft total right-of-way widths are typical for the types of projects it expects to review and that actual width depends on line type, voltage, and safe operation. The application deliberately uses the conservative end of that stated range. This is not a parcel-specific easement width. Before design, review title documents, survey the easement, identify the line and operator, and obtain current structure, access, and vegetation restrictions.

### Configurability and auditability

`backend/config.json` versions the default profile, footprint-only comparison profile, minimum and maximum values, input increments, geometry basis, rationale, source URLs, and field-verification guidance. Every analysis response includes the config version, profile ID, exact enabled-layer setbacks, and policy snapshot. Users can change setbacks or disable layers through the request and UI without editing source code.

Changing a default is therefore a policy/configuration operation, not a geometry-code change. In production, policy versions should be immutable once used in a decision record, and jurisdiction-specific profiles should be reviewed by the relevant planner, environmental consultant, surveyor, and counsel.

## Main tradeoffs

### SQLite instead of PostGIS

SQLite plus R-tree provides a zero-service, reproducible demo and performs indexed parcel-scale lookups well. It avoids asking reviewers to provision a database. The cost is limited write concurrency, no native spatial predicates, no database-side buffering/union, and no shared query planner or connection pool. Python must deserialize candidate GeoJSON before exact operations.

### Synchronous API instead of a job queue

Most parcel analyses in the bounded sample finish within an interactive request, so a synchronous API is simpler and makes cancellation straightforward. Very complex parcels or dense source data can tie up a worker. A production system needs a time budget, complexity guardrails, and an asynchronous job path for expensive overlays and batch analysis.

### Dynamic buffers instead of precomputing every policy result

Setbacks are user-configurable, so precomputing all possible buffered geometries is not practical. The application pre-clips raw source data at ingestion and caches commonly repeated parcel/layer/setback results for 120 seconds. This favors interactive experimentation while keeping policy flexible. A small discrete set of organization-wide policies could additionally be materialized during ingestion.

### GeoJSON instead of vector tiles for selected-parcel results

Raw GeoJSON is simple, inspectable, and appropriate after results have been clipped to one parcel. It becomes inefficient for county-wide browsing. The project supports optional PMTiles for overview constraints and switches to clipped GeoJSON once a parcel is selected. A production deployment should not send a complete county wetland layer as one GeoJSON response.

### Ordered attribution instead of proportional overlap allocation

Assigning overlap to the first configured layer makes totals deterministic and easy to explain. It does mean a layer's `removed_acres` is not its standalone impact. Gross and overlap values are returned so reviewers can see that distinction. Proportional allocation would appear neutral but is harder to audit and has no clear regulatory meaning.

### Screening defaults instead of pretending to encode law

Configurable defaults make the application immediately useful, but no single setback is legally correct across jurisdictions and projects. The UI and response preserve assumptions and verification steps rather than presenting defaults as authoritative rules. The system favors transparent uncertainty over false precision.

## Performance and growth behavior

### Current measured behavior

On the development machine, a 200-run measurement using the checked-in parcel and three default layers produced a 3.64 ms median, 4.67 ms p95, and 7.53 ms maximum. These figures describe a small bounded catalog and should not be interpreted as county- or statewide capacity results.

On the overlap-heavy fixture, direct geometry work measured 17.5 ms cold and 7.3 ms median warm, approximately a 2.4x improvement from buffer reuse. Display simplification reduced one response from 19.9 KB to 13.4 KB, and gzip reduced it to 3.9 KB. These measurements demonstrate the direction of the optimizations, not a formal service-level objective.

### Work that scales well

- Parcel search by bounding box scales approximately with R-tree candidate count rather than total table size.
- Constraint selection also uses an R-tree and an expanded parcel bounding box, so parcels far from a layer do not pay for that layer's geometry work.
- Empty layers short-circuit before projection, buffer, and union.
- County/region clipping happens during ingestion rather than on every request.
- Full-precision and display geometries are stored separately, so map payload does not grow with analysis precision.
- Enabled layer previews run concurrently and do not block the initial parcel outline.
- Gzip compresses verbose GeoJSON effectively.
- MapLibre sources remain mounted and are updated in place, avoiding layer recreation and flicker.

### Dominant costs as data grows

The critical variable is not the total number of rows alone; it is the number and complexity of features intersecting one parcel's setback-expanded bounding box. A million well-indexed features can be manageable if a request retrieves ten simple candidates. A single highly detailed wetland polygon with hundreds of thousands of vertices can be slow even in a small database.

The main costs are:

1. Reading and JSON-decoding candidate geometries from SQLite.
2. Projecting every candidate vertex into UTM.
3. Unioning fragmented or overlapping features within a layer.
4. Buffering complex boundaries, which can create many additional vertices.
5. Difference/intersection operations between exclusion unions and intricate parcel boundaries.
6. Serializing and transmitting the resulting GeoJSON.
7. Rendering large vertex counts in the browser.

GEOS overlay cost is sensitive to topology and vertex count and is not linear in all cases. Dense NWI or floodplain data, long transmission networks retrieved by an overly broad bounding box, sliver polygons, and invalid geometry are likely to expose strain before raw parcel count does.

### Cache behavior and concurrency

The in-process cache stores up to 256 projected, buffered exclusions for 120 seconds, keyed by parcel, layer, setback, and config version. It is effective when users revisit common parcels and defaults. It is less effective when every request uses a unique setback or parcel. Each Uvicorn worker has its own cache, so additional workers improve concurrency but fragment cache locality and duplicate memory.

SQLite supports many readers but is not the right shared store for concurrent ingestion and interactive analysis. The current container runs one application process; CPU-heavy GEOS operations can reduce throughput because each request occupies that worker even when the database query is fast. Horizontal replicas would each carry their own catalog and cache.

### Where this implementation starts to strain

There is no defensible universal row-count threshold without representative source data and load testing. Operationally, I would treat the following as migration signals:

- Parcel-scoped candidate queries regularly return hundreds or thousands of complex features.
- Cold p95 analysis exceeds roughly 1-2 seconds for ordinary parcels.
- Simplified selected-parcel responses reach several megabytes compressed or browser interaction drops frames.
- Geometry repair, buffer, or union causes sustained high CPU or request timeouts.
- The 256-entry cache churns continuously and hit rate remains low.
- More than one county must be updated independently or source snapshots must remain queryable by version.
- Multiple analysts require concurrent ingestion, scenario persistence, or audit writes.
- Batch analysis competes with interactive traffic.

At that point, adding more API workers alone will not solve the underlying candidate, geometry, and data-management costs.

### Production scaling path

1. Move parcels and constraints to PostGIS with appropriate SRIDs and GiST indexes on every authoritative geometry column.
2. Partition or cluster source tables by state/county and source version; preserve immutable acquisition metadata.
3. Use database-side bounding-box and exact intersection filtering so Python receives only relevant geometry.
4. Use bulk `COPY` and offline validation/simplification during ingestion.
5. Materialize common policy buffers or subdivide very large polygons with `ST_Subdivide` where benchmarks justify it.
6. Add a bounded database connection pool and separate interactive workers from ingestion and batch workers.
7. Put expensive analyses into cancellable jobs with progress, idempotency keys, timeouts, and stored results.
8. Move reusable buffers/results to a shared cache keyed by immutable source and policy versions, with explicit memory limits.
9. Serve county/state overview data as versioned vector tiles or PMTiles through object storage and a CDN.
10. Define performance budgets for candidate count, vertices, compressed response size, cold/warm p50/p95/p99, and concurrent users; test against representative dense urban, coastal, riverine, and rural parcels.

## Validation and trust

Automated tests cover projected acreage, two-decimal rounding, complete layer overlap, total reconciliation, restore clipping, invalid bow-tie repair, real public parcel/wetland geometry, empty-layer short-circuiting, cache reuse, policy profiles, setback bounds, assumption snapshots, parcel pagination and bounding-box lookup, API validation, compression, and map export timing.

For production, I would add:

- Golden analyses reviewed in desktop GIS against source snapshots.
- Property-based tests for geometry validity and acreage invariants.
- Fuzz tests using malformed and extreme GeoJSON.
- Load tests split by candidate count and vertex complexity rather than only request count.
- Regression benchmarks for cold/warm geometry time, payload size, and browser frame rate.
- Source freshness, rejected-feature, repair-rate, and missing-layer alerts.
- An audit record tying each result to source versions, policy version, user, manual edits, and timestamp.

## Where it breaks and what I would do next

### Data completeness and legal reliance

The largest current limitation is data completeness, not geometry code. The checked-in sample contains only a small Bell County parcel window and one NWI feature; FEMA and transmission support are demonstrated through the model and fixtures rather than a complete local extract. The next step is to ingest current county-wide NWI, effective FEMA NFHL, and transmission data, record acquisition timestamps and licenses, and publish coverage status per layer.

Parcel geometry is appraisal mapping, not surveyed ownership. NWI is screening data, not a delineation. HIFLD centerlines are not easement polygons. FEMA mapping may be revised or superseded by local studies. The application must never convert those source limitations into a definitive "buildable" claim.

### Geometry edge cases

Centroid-selected UTM is appropriate for normal parcels but is not a universal CRS strategy for very large properties, parcels crossing a zone boundary, or analyses spanning multiple distant geometries. Large multipart holdings should be subdivided or evaluated in an approved regional projection. Geometry repair can also change pathological source shapes; production ingestion should quarantine major repairs for review rather than silently accept all valid output.

### Missing planning constraints

A real feasibility screen commonly also needs recorded easements, road and property-line setbacks, building footprints, steep slopes, soils, protected habitat, cultural resources, water/sewer availability, zoning, and local overlays. These were excluded because each requires a credible local source and policy interpretation. Adding layers without source quality, geometry semantics, and verification guidance would make the product look complete while reducing trust.

### Workflow and governance

Manual restore is intentionally powerful for scenario exploration, but a production restore should require a reason, evidence attachment, reviewer identity, approval state, and immutable history. Share links currently encode scenario state; sensitive projects need authenticated storage, authorization, retention controls, and redacted exports.

### Immediate next increments

1. Load and verify complete Bell County constraint snapshots and expose coverage/freshness metadata in the UI.
2. Benchmark dense and complex parcels, then set candidate, vertex, response-size, and request-time limits.
3. Implement the PostGIS repository behind the existing interface and compare results against SQLite golden cases.
4. Add source-versioned scenario persistence and an auditable manual-restore workflow.
5. Add jurisdiction-specific policy profiles reviewed by domain professionals.
6. Expand the constraint model only when each new layer has an authoritative source, explicit geometry interpretation, configurable rule, and verification path.

The architecture is intentionally sufficient for a credible parcel-screening demonstration and a moderate county deployment, but production readiness ultimately depends on current source coverage, domain governance, operational observability, and explicit limits as much as on overlay performance.
