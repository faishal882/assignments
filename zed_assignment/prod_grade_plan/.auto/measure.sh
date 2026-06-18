#!/usr/bin/env bash
set -euo pipefail
PLAN="plans/buildable-area-production-plan.md"
if [[ ! -f "$PLAN" ]]; then
  echo "METRIC plan_score=0"
  echo "METRIC word_count=0"
  echo "METRIC section_count=0"
  echo "METRIC todo_count=999"
  exit 0
fi
text=$(tr '[:upper:]' '[:lower:]' < "$PLAN")
words=$(wc -w < "$PLAN" | tr -d ' ')
sections=$(grep -c '^##' "$PLAN" || true)
todos=$(grep -Eic 'todo|tbd|coming soon|placeholder|\?\?' "$PLAN" || true)
risks=$(grep -Eic 'risk|failure mode|mitigation|tradeoff|assumption' "$PLAN" || true)
sources=$(grep -Eic 'tnris|usfws|nwi|fema|hifld|usgs|osm|openstreetmap|microsoft building footprints|epa|protected areas' "$PLAN" || true)
runbooks=$(grep -Eic 'runbook|alert|slo|rollback|backup|restore|incident|observability|metrics|trace' "$PLAN" || true)
score=0
require() {
  local name="$1" pattern="$2" weight="$3"
  if grep -Eiq "$pattern" "$PLAN"; then score=$((score + weight)); else echo "MISSING $name" >&2; fi
}
require "executive summary" 'executive summary|north star|product goal' 4
require "domain model" 'domain model|parcel|constraint|exclusion|manual adjustment|scenario' 5
require "backend" 'fastapi|backend architecture|api gateway|service layer' 7
require "frontend" 'react|maplibre|arcgis|frontend architecture|map interaction' 7
require "spatial database" 'postgis|spatial index|gist|st_subdivide|geometry' 8
require "data ingestion" 'ingestion|etl|ogr2ogr|tippecanoe|validation|lineage' 8
require "public data sources" 'tnris|usfws|national wetlands inventory|fema|hifld|openstreetmap|microsoft building footprints' 7
require "geometry algorithm" 'union|difference|intersection|buffer|st_makevalid|topology' 9
require "setbacks configurable" 'configurable setback|setback.*config|request parameter|scenario config' 8
require "manual carve restore" 'carve|restore|draw|manual edit|add back' 8
require "area compatibility" 'epsg:3857|web mercator|planar area|round.*acre' 7
require "api contracts" 'openapi|endpoint|request|response|schema' 7
require "async jobs" 'celery|rq|background job|queue|worker|async' 4
require "caching" 'cache|etag|tile cache|redis' 5
require "performance" 'performance|scal|benchmark|p95|latency|throughput' 8
require "security" 'auth|authorization|rate limit|csrf|csp|security' 6
require "observability" 'observability|metrics|logs|traces|opentelemetry|slo' 6
require "testing" 'unit test|integration test|property|golden|e2e|load test' 8
require "deployment" 'docker|compose|kubernetes|terraform|ci/cd|deployment' 6
require "runbook" 'runbook|rollback|backup|restore|incident' 5
require "phases" 'phase 0|phase 1|milestone|delivery plan|vertical slice' 5
require "risks" 'risk register|failure mode|mitigation' 5
require "writeup" 'approach writeup|decisions|calls made|tradeoffs' 4
require "tenancy and permissions" 'tenant|workspace|role-based|rbac|organization' 4
require "schema migrations" 'alembic|migration|backward compatible|expand.*contract|schema version' 4
require "data quality gates" 'data quality|quarantine|checksum|lineage|validation report|acceptance threshold' 5
require "tile pipeline" 'vector tile|pmtiles|tippecanoe|tilejson|tile generation' 4
require "cost controls" 'cost|budget|quota|autoscal|capacity' 3
require "decision records" 'adr|architecture decision record|decision log' 3
require "auditability" 'audit trail|audit log|immutable|input fingerprint|reproducible' 5
require "jurisdiction profiles" 'jurisdiction profile|local ordinance|ordinance|county profile|rule profile' 4
require "ha dr" 'high availability|disaster recovery|rpo|rto|failover' 4
require "admin operations" 'admin|operator|dataset publish|disable.*dataset|feature flag' 3
require "accessibility" 'accessibility|wcag|keyboard|screen reader|color contrast' 4
require "frontend performance" 'frontend performance|web worker|debounce|virtualize|bundle|render budget' 4
require "browser resilience" 'offline|retry|network error|error boundary|recoverable' 3
require "precision and slivers" 'precision grid|snap|sliver|st_snap|st_reduceprecision|tolerance' 5
require "manual edit policy" 'restore policy|carve-out policy|outside parcel|cannot restore|edit policy' 4
require "large geometry handling" 'st_subdivide|vertex count|simplif|generaliz|pathological geometry' 4
require "threat model" 'threat model|spoofing|tampering|repudiation|information disclosure|denial of service|privilege escalation' 5
require "acceptance criteria" 'acceptance criteria|definition of done|given.*when.*then|must pass' 4
require "open questions" 'open question|assumption to validate|confirm with evaluator|decision needed' 3
require "idempotency" 'idempotency|idempotent|request id|dedup|retry-safe' 4
require "concurrency controls" 'concurrency|optimistic lock|version conflict|transaction isolation|race condition' 4
require "api error model" 'error code|problem\+json|validation error|conflict|unprocessable' 3
require "licensing compliance" 'license|terms of use|attribution|redistribution|data license' 4
require "pii handling" 'pii|personally identifiable|redact|data minimization|privacy' 4
require "data refresh" 'refresh cadence|scheduled refresh|incremental update|staleness|source date' 4
require "implementation backlog" 'work breakdown|backlog|ticket|issue|user story|vertical slice' 4
require "team roles" 'role|staffing|owner|responsible|raci|team' 3
require "timeline estimates" 'week|timeline|duration|sprint|estimate' 3
require "performance test matrix" 'performance test matrix|load profile|benchmark scenario|stress test|soak test' 4
require "spatial sql examples" 'select .*st_|create index .*gist|explain analyze|spatial sql' 4
require "cache invalidation" 'cache invalidation|invalidate|cache key|input fingerprint' 3
require "county selection" 'county selection|choose.*county|sampling|feature count|manageable parcel' 3
require "demo reproducibility" 'demo parcel|seed data|fixture|snapshot|reproducible demo' 3
require "graceful degradation" 'degraded mode|graceful degradation|fallback|read-only mode|partial outage' 3
require "sequence flow" 'sequence diagram|request flow|analysis flow|user flow|status polling' 4
require "job lifecycle" 'job lifecycle|queued|running|complete|failed|cancel|retry' 4
require "export/reporting" 'export|pdf|csv|geojson|report|share' 3
require "responsive design" 'responsive|mobile|tablet|viewport|touch' 3
require "browser compatibility" 'browser compatibility|chrome|firefox|safari|cross-browser' 3
require "ux empty loading states" 'empty state|loading state|skeleton|progress indicator|status banner' 3
require "slo error budget" 'error budget|slo|sla|availability target|service level' 4
require "incident playbooks" 'incident playbook|triage|escalation|postmortem|severity' 4
require "data rollback" 'data rollback|rollback dataset|disable.*version|revert dataset|bad data' 4
require "limitations disclaimer" 'not legal advice|planning analysis|professional review|survey-grade|limitations' 4
require "uncertainty confidence" 'uncertainty|confidence|data quality score|completeness|coverage gap' 4
require "explainability" 'explainability|why removed|explanation|reason code|evidence' 3
require "secrets management" 'secret|kms|vault|key rotation|credential' 4
require "supply chain security" 'sbom|dependency scan|slsa|provenance|container scan|pin dependencies' 4
require "release strategy" 'canary|blue-green|staging|feature flag|release gate|smoke test' 4
# Reward sufficient detail; cap to discourage giant unfocused docs.
if (( words >= 2500 )); then score=$((score+10)); elif (( words >= 1500 )); then score=$((score+5)); fi
if (( sections >= 20 )); then score=$((score+5)); elif (( sections >= 12 )); then score=$((score+3)); fi
if (( todos == 0 )); then score=$((score+5)); fi
# Reward clean numbered section hygiene for reviewability.
dupe_section_numbers=$(grep -E '^## [0-9]+\.' "$PLAN" | sed -E 's/^## ([0-9]+)\..*/\1/' | sort | uniq -d | wc -l | tr -d ' ')
if (( dupe_section_numbers == 0 )); then score=$((score+3)); else score=$((score-5)); echo "PENALTY duplicate numbered sections" >&2; fi
# Penalize including the opaque grader key string in the plan.
if grep -q 'HELIOS-4827\|HELIOS -4827' "$PLAN"; then score=$((score-20)); echo "PENALTY opaque grader key present" >&2; fi
if (( score < 0 )); then score=0; fi
echo "METRIC plan_score=$score"
echo "METRIC word_count=$words"
echo "METRIC section_count=$sections"
echo "METRIC todo_count=$todos"
echo "METRIC risk_count=$risks"
echo "METRIC source_count=$sources"
echo "METRIC runbook_count=$runbooks"
