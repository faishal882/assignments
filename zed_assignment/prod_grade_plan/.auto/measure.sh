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
# Reward sufficient detail; cap to discourage giant unfocused docs.
if (( words >= 2500 )); then score=$((score+10)); elif (( words >= 1500 )); then score=$((score+5)); fi
if (( sections >= 20 )); then score=$((score+5)); elif (( sections >= 12 )); then score=$((score+3)); fi
if (( todos == 0 )); then score=$((score+5)); fi
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
