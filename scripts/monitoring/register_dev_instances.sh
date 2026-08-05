#!/usr/bin/env bash
# Register pulse-db self-monitoring + optional sibling Postgres DBs (idempotent).
#
# Usage (from repo root, app container must be running):
#   bash scripts/monitoring/register_dev_instances.sh
#
# Local backend (no Docker app container):
#   cd backend && PULSEDB_SELF_HOST=localhost .venv/bin/python cli.py monitoring register-dev-instances
#
# sql-monitor Postgres (port 5433) — grant pg_monitor once if needed:
#   docker exec -it <sql-monitor-postgres-container> psql -U sqlmonitor -d sql_monitor \
#     -c "GRANT pg_monitor TO sqlmonitor;"
#
# sql-monitor's metadata DB is mostly idle pool connections. The Waits chart needs
# state='active' sessions — run dev workload in another terminal if the chart is empty:
#   bash scripts/monitoring/sql_monitor_dev_workload.sh
#
# taxorder-ksef Postgres has no host port — app/scheduler must join network taxorder-ksef-dev
# (docker-compose). Grant pg_monitor once:
#   docker exec -it taxorder-ksef-db-dev psql -U taxorder-ksef -d taxorder-ksef \
#     -c 'GRANT pg_monitor TO "taxorder-ksef";'
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/lib/detect_compose.sh
source "$PROJECT_DIR/scripts/lib/detect_compose.sh"

if [ -z "${COMPOSE_DIR:-}" ] || [ -z "${COMPOSE_FILE:-}" ]; then
  compose_context=$(detect_compose_context)
  COMPOSE_DIR="${compose_context%%|*}"
  COMPOSE_FILE="${compose_context##*|}"
fi

ensure_taxorder_network() {
  local network=taxorder-ksef-dev
  if ! docker network inspect "$network" >/dev/null 2>&1; then
    echo "Docker network '$network' missing — start taxorder-ksef or: docker network create $network" >&2
    return 0
  fi
  for container in pulse-db-app pulse-db-scheduler; do
    if docker inspect "$container" >/dev/null 2>&1; then
      if ! docker inspect "$container" --format '{{json .NetworkSettings.Networks}}' | grep -q "\"$network\""; then
        echo "Connecting $container to $network..."
        docker network connect "$network" "$container" || true
      fi
    fi
  done
}

ensure_taxorder_network

cd "$COMPOSE_DIR"
docker compose -f "$COMPOSE_FILE" exec app python cli.py monitoring register-dev-instances --repair
