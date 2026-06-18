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
require "data qa thresholds" 'acceptance threshold|validation threshold|qa gate|publish gate|quality gate' 4
require "dataset diff review" 'dataset diff|change report|before/after|acreage delta|material change' 4
require "human approval workflow" 'approval workflow|human review|reviewer sign-off|two-person|approve.*publish' 3
require "api versioning" 'api version|/v1|versioned api|semantic version|backward compatible' 4
require "deprecation policy" 'deprecation|sunset|migration window|breaking change|compatibility window' 4
require "contract testing" 'contract test|consumer-driven|openapi diff|schema compatibility|client compatibility' 4
require "database operations" 'vacuum|analyze|autovacuum|connection pool|pgbouncer|query timeout' 4
require "partitioning archival" 'partition|archive|retention|cold storage|table bloat|maintenance window' 3
require "query safeguards" 'statement timeout|query budget|slow query|kill.*query|resource limit' 3
require "support model" 'support model|support tier|help desk|support queue|customer support|on-call handoff' 4
require "user documentation" 'user guide|operator guide|training|tooltip|documentation' 3
require "feedback loop" 'feedback loop|user feedback|issue intake|feature request|support ticket|triage' 3
require "cdn edge caching" 'cdn|edge cache|cache-control|signed url|tile cache' 4
require "basemap resilience" 'basemap|tile provider|fallback map|offline tiles|provider outage' 4
require "tile security" 'signed tile|tile url|referer restriction|token|hotlink' 3
require "governance board" 'governance board|steering committee|review board|change advisory|approval board' 3
require "expert validation" 'subject matter expert|sme|licensed professional|legal review|environmental consultant|civil engineer' 4
require "policy change management" 'policy change|rule change|ordinance update|effective date|change log|rule history' 4
require "synthetic monitoring" 'synthetic monitor|synthetic check|heartbeat|probe|canary scenario' 4
require "resilience drills" 'chaos|game day|failure injection|resilience drill|disaster drill' 4
require "autoscaling strategy" 'autoscaling|scale up|scale down|horizontal pod autoscaler|queue depth|scaling trigger' 3
require "legal terms" 'terms of use|privacy policy|acceptable use|disclaimer|liability' 4
require "data subject requests" 'data subject request|dsr|delete account|export data|right to deletion|privacy request' 3
require "compliance artifacts" 'accessibility conformance|vp[ao]t|soc 2|compliance artifact|security questionnaire|dpa' 3
require "usage metering" 'usage metering|metered|usage record|billing|chargeback|cost attribution' 4
require "queue fairness" 'fair queue|priority queue|tenant fairness|starvation|noisy neighbor|weighted' 4
require "entitlements" 'entitlement|plan limit|feature access|quota tier|subscription|billing plan' 3
require "report integrity" 'signed report|report signature|tamper-evident|checksum|verification' 4
require "share links" 'share link|public link|expiring link|revocation|recipient' 3
require "export provenance" 'export provenance|report metadata|watermark|citation|generated at' 3
require "unit policy" 'unit policy|unit conversion|acres|square feet|hectare|measurement units' 4
require "localization" 'localization|i18n|locale|timezone|date format|number format' 3
require "numeric precision" 'decimal precision|rounding mode|significant digits|precision policy|acreage precision' 4
require "scenario branching" 'scenario branch|clone scenario|what-if|compare scenarios|version timeline' 4
require "edit history" 'edit history|undo|redo|edit log|revision history' 4
require "collaboration conflicts" 'collaboration|concurrent edit|conflict resolution|merge|presence' 3
require "county onboarding" 'county onboarding|new county|county rollout|onboarding checklist|source mapping' 4
require "regional partitioning" 'regional partition|county partition|geographic shard|multi-county|jurisdiction boundary' 4
require "schema mapping registry" 'schema mapping|field mapping|crosswalk|mapping registry|attribute normalization' 3
require "transactional outbox" 'transactional outbox|outbox table|exactly-once|at-least-once|event delivery' 4
require "webhooks integrations" 'webhook|integration|external system|callback|subscription event' 4
require "event taxonomy" 'domain event|event taxonomy|scenario.*completed|dataset.*published|event schema' 3
require "parcel identity lifecycle" 'parcel identity|apn normalization|parcel split|parcel merge|parcel lifecycle|assessor id' 4
require "address search normalization" 'address normalization|geocoding|situs|search ranking|fuzzy search' 3
require "parcel lineage" 'parcel lineage|predecessor|successor|historic parcel|parcel version' 4
require "constraint taxonomy" 'constraint taxonomy|constraint classification|layer taxonomy|reason taxonomy|constraint type' 4
require "attribute normalization" 'attribute normalization|normalized attribute|class mapping|source attribute|attribute crosswalk' 4
require "constraint confidence" 'constraint confidence|confidence score|source confidence|evidence strength|uncertain constraint' 3
require "dataset canary rollout" 'dataset canary|canary publish|rollout cohort|limited rollout|blast radius' 4
require "shadow recompute" 'shadow recompute|shadow analysis|parallel run|compare output|dry-run publish' 4
require "rollback criteria" 'rollback criteria|abort rollout|promotion gate|rollback threshold|stop condition' 3
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
