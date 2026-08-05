#!/usr/bin/env bash
# Start (or restart) the monitoring scheduler container.
#
# Usage:
#   bash scripts/monitoring/run_scheduler.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/lib/detect_compose.sh
source "$PROJECT_DIR/scripts/lib/detect_compose.sh"

if [ -z "${COMPOSE_DIR:-}" ] || [ -z "${COMPOSE_FILE:-}" ]; then
  compose_context=$(detect_compose_context)
  COMPOSE_DIR="${compose_context%%|*}"
  COMPOSE_FILE="${compose_context##*|}"
fi

cd "$COMPOSE_DIR"
docker compose -f "$COMPOSE_FILE" up -d scheduler
docker compose -f "$COMPOSE_FILE" logs scheduler --tail 20
