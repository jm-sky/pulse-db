#!/usr/bin/env bash
# Generate light Postgres activity on sql-monitor's metadata DB so PulseDB's
# session sampler (state = 'active' only) can observe sessions for ash rollups.
#
# sql-monitor-postgres is mostly idle connection-pool traffic — without workload
# the Waits chart stays empty even when the collector connects successfully.
#
# Usage:
#   bash scripts/monitoring/sql_monitor_dev_workload.sh          # run until Ctrl+C
#   bash scripts/monitoring/sql_monitor_dev_workload.sh --once   # one burst (~30s)
set -euo pipefail

ONCE=false
if [[ "${1:-}" == "--once" ]]; then
  ONCE=true
fi

PG_CONTAINER="${SQL_MONITOR_PG_CONTAINER:-sql-monitor-postgres-1}"
PG_USER="${SQL_MONITOR_PG_USER:-sqlmonitor}"
PG_DB="${SQL_MONITOR_PG_DATABASE:-sql_monitor}"
SLEEP_SEC="${SQL_MONITOR_DEV_WORKLOAD_SLEEP_SEC:-0.25}"
INTERVAL_SEC="${SQL_MONITOR_DEV_WORKLOAD_INTERVAL_SEC:-0.3}"

if ! docker inspect "$PG_CONTAINER" >/dev/null 2>&1; then
  echo "Container not found: $PG_CONTAINER (set SQL_MONITOR_PG_CONTAINER)" >&2
  exit 1
fi

echo "Dev workload on $PG_CONTAINER ($PG_DB) — sleep=${SLEEP_SEC}s interval=${INTERVAL_SEC}s"

run_burst() {
  for _ in $(seq 1 30); do
    docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -q -c "SELECT pg_sleep($SLEEP_SEC);" >/dev/null
    sleep "$INTERVAL_SEC"
  done
}

if $ONCE; then
  run_burst
  echo "Done."
  exit 0
fi

while true; do
  run_burst
done
