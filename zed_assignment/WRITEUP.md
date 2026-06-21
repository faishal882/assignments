# Buildable Area Analysis — Engineering Writeup

## Architecture and scope

FastAPI owns a focused geometry engine and a repository interface; React and MapLibre own interaction and rendering. This keeps acreage reproducible, prevents browser geometry implementations from becoming a second source of truth, and leaves a clean seam for replacing the checked-in fixture repository with PostGIS. MapLibre was selected over ArcGIS to avoid accounts, API keys, and service credits when the system only needs a basemap and GeoJSON rendering.

This is intentionally a synchronous, single-parcel planning tool. It does not include auth, billing, collaboration, a job queue, legal certification, or nationwide data management.

## Geometry and attribution

All transport geometry is WGS84. For each request, the backend chooses the WGS84 UTM zone containing the parcel centroid. It repairs input geometry, projects it, applies metre setbacks, clips constraints to the parcel, unions exclusions, and computes acreage from projected square metres. UTM is materially more defensible for parcel-scale distance and area than Web Mercator; output is rounded to two decimals rather than forced upward.

Constraints are processed in the request/config order. Each breakdown row reports:

- `removed_acres`: the layer’s exclusive incremental removal; these values reconcile with the total.
- `gross_acres`: its full clipped extent before overlap attribution.
- `overlap_acres`: the part already attributed to an earlier layer.

The response also reports duplicate overlap across automatic layers. Carve-outs remove only land still buildable. Restores add back excluded land but are intersected with the original parcel, so they cannot expand ownership geometry.

## Data choices and assumptions

The app models TNRIS parcels, USFWS NWI wetlands, FEMA high-risk flood hazards, and HIFLD transmission lines. Defaults are explicitly versioned screening policy, not claims of universal law:

- Wetlands use 50 ft (15.24 m) from the mapped polygon edge. This is a conservative early-review assumption; Section 404 and state/local rules do not establish one universal setback. A current delineation and governing local requirements must replace it before design.
- Flood hazards use the mapped polygon with 0 ft additional lateral buffer. FEMA floodway controls concern encroachment and no-rise analysis, while freeboard is vertical and cannot be represented by a planar setback.
- Transmission uses 100 ft (30.48 m) each side of the mapped centerline, representing the upper end of FERC's typical 100-200 ft total right-of-way range for applicable projects. Recorded easements, voltage, surveys, and operator restrictions control.

`backend/config.json` owns profile values, input bounds, increments, rationale, geometry basis, source guidance, and verification instructions. The backend validates overrides and embeds the complete versioned assumption snapshot in every analysis result. The UI can switch between the planning screen and footprint-only baseline, then marks any layer toggle or distance edit as a custom override.

Building footprints and PAD-US were not included. They can be useful, but three well-attributed constraints better demonstrate correct buffering and overlap than extra layers without a jurisdiction-specific rule.

## Interaction design

The UI requests parcels and layer controls from the API rather than duplicating configuration. Setback edits are debounced and stale requests are aborted. Users can toggle layers, draw named carve-outs/restores, remove individual edits, inspect constraint reasons and setbacks on the map, and see exclusive versus overlap acreage.

## Validation and performance

Automated tests cover known projected area, non-ceiling rounding, complete layer overlap, restore clipping, invalid bow-tie repair, policy profiles, layer-specific bounds, assumption snapshots, parcel lookup, analysis contracts, and clean validation errors. A local 200-run measurement of the checked-in parcel and all three default layers produced a 3.64 ms median, 4.67 ms p95, and 7.53 ms maximum on the development machine. These numbers describe the synthetic fixture, not county-scale source complexity.

The checked-in runtime uses SQLite R-tree indexes and performs a setback-expanded bbox candidate query before exact projected intersection. Ingestion clips every source to a named county/acquisition region once and stores two representations: full precision for measurement and a topology-preserving simplified copy for display. Analysis output is simplified again at a 0.25 m projected tolerance, after acreage has been calculated from full geometry.

Automatic exclusions are buffered per layer, attributed in policy order for non-duplicated breakdown totals, then combined with one `unary_union` and subtracted from the parcel once. Layers with no bbox candidates skip projection, union, and buffer work. A thread-safe 120-second, 256-entry cache reuses projected buffered exclusions by parcel, layer, setback, and config version. On the overlap-heavy fixture, direct geometry work measured 17.5 ms cold and 7.3 ms median warm (2.4x); simplification reduced the JSON response from 19.9 KB to 13.4 KB, and gzip reduced it to 3.9 KB.

The browser first renders the simplified parcel outline, requests enabled layer previews concurrently, and then replaces them with the final reconciled result. MapLibre sources remain mounted and update through `setData`; a short opacity transition and retained ghost boundary make geometry changes trackable. Optional PMTiles provide county-scale browsing without loading county GeoJSON. Skeleton totals, per-layer loading/empty/error states, and a delayed 1.5-second complexity message cover perceived latency.

## Limitations and next steps

The default catalog is a bounded real-data slice: 363 standardized Bell County appraisal polygons from the TxGIO/TNRIS parcel program and a locally clipped USFWS NWI Version 2 riverine feature. Duplicate appraisal IDs are handled with a stable FIPS/property/source-object composite key; missing addresses fall back to legal descriptions. The larger overlap fixture remains available for deterministic tests.

SQLite plus R-tree indexes is deliberate for a self-contained take-home and handles a moderate county without scanning every geometry. Full multi-county production would move the same repository contract to PostGIS, use GiST indexes and a bounded connection pool, run expensive overlays as cancellable jobs, and version source snapshots. The in-process TTL cache is per worker; a multi-worker deployment should use a shared cache keyed by immutable source/config versions or accept worker-local warming. Production work also requires source-license review, current FEMA/NWI classification filters, and ingestion observability. A permitting workflow would additionally require restore audit identity, evidence, and approval state.
