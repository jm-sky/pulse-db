#!/usr/bin/env bash
# Deploy pulse-db: git pull, frontend build, backend restart + migrations.
# Auto-detects the active Docker Compose stack from the running app container.
#
# Usage:
#   bash scripts/deploy.sh           # auto-detect, or prod default if no container
#   bash scripts/deploy.sh --prod    # force root docker-compose.yml
#   bash scripts/deploy.sh --dev     # force docker-compose.dev.yml
#   bash scripts/deploy.sh --help
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
APP_CONTAINER_NAME="pulse-db-app"

# shellcheck source=scripts/lib/detect_compose.sh
source "$SCRIPTS_DIR/lib/detect_compose.sh"

COMPOSE_DIR=""
COMPOSE_FILE=""
COMPOSE_SOURCE=""
FORCE_MODE=""

usage() {
  cat <<EOF
Usage: bash scripts/deploy.sh [OPTIONS]

Deploy pulse-db: pull, build frontend, restart backend, run migrations.

Options:
  --prod    Force prod stack (root docker-compose.yml)
  --dev     Force dev stack (docker-compose.dev.yml)
  --help    Show this help

Default behaviour:
  - If pulse-db-app is running: auto-detect compose from container labels
  - If no container is running: use prod stack (root docker-compose.yml)

GitHub Actions uses the same script with auto-detection.
EOF
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --prod)
        FORCE_MODE="prod"
        ;;
      --dev)
        FORCE_MODE="dev"
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        echo -e "${RED}Error: Unknown option: $1${NC}" >&2
        usage >&2
        exit 1
        ;;
    esac
    shift
  done
}

resolve_compose_for_deploy() {
  local compose_context=""
  local running_compose_dir=""
  local running_compose_file=""

  if [ "$FORCE_MODE" = "prod" ]; then
    COMPOSE_DIR="$PROJECT_DIR"
    COMPOSE_FILE="docker-compose.yml"
    COMPOSE_SOURCE="forced (--prod)"
  elif [ "$FORCE_MODE" = "dev" ]; then
    COMPOSE_DIR="$PROJECT_DIR"
    COMPOSE_FILE="docker-compose.dev.yml"
    COMPOSE_SOURCE="forced (--dev)"
  elif is_app_container_running; then
    compose_context=$(detect_compose_context)
    COMPOSE_DIR="${compose_context%%|*}"
    COMPOSE_FILE="${compose_context##*|}"
    COMPOSE_SOURCE="auto-detected"
  else
    COMPOSE_DIR="$PROJECT_DIR"
    COMPOSE_FILE="docker-compose.yml"
    COMPOSE_SOURCE="default (prod, no running container)"
  fi

  if [ -z "$COMPOSE_FILE" ] || [ -z "$COMPOSE_DIR" ]; then
    echo -e "${RED}Error: Could not resolve docker-compose context${NC}" >&2
    echo -e "${YELLOW}Use --prod or --dev, or start the app container first.${NC}" >&2
    exit 1
  fi

  if [ ! -f "$COMPOSE_DIR/$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: Docker Compose file not found: $COMPOSE_DIR/$COMPOSE_FILE${NC}" >&2
    exit 1
  fi

  if [ -n "$FORCE_MODE" ] && is_app_container_running; then
    compose_context=$(detect_compose_context)
    running_compose_dir="${compose_context%%|*}"
    running_compose_file="${compose_context##*|}"
    if [ "$running_compose_dir" != "$COMPOSE_DIR" ] || [ "$running_compose_file" != "$COMPOSE_FILE" ]; then
      echo -e "${YELLOW}Warning: Running container uses ${running_compose_dir}/${running_compose_file}, deploying ${COMPOSE_DIR}/${COMPOSE_FILE} instead.${NC}"
    fi
  fi
}

compose_display_path() {
  local display="${COMPOSE_DIR#"$PROJECT_DIR"/}"
  if [ "$display" = "$COMPOSE_DIR" ]; then
    echo "$COMPOSE_DIR/$COMPOSE_FILE"
  else
    echo "$display/$COMPOSE_FILE"
  fi
}

parse_args "$@"
resolve_compose_for_deploy

echo -e "${GREEN}Starting pulse-db deployment...${NC}"
echo -e "${GREEN}Using compose: $(compose_display_path) (${COMPOSE_SOURCE})${NC}"

setup_toolchain() {
  if command -v pnpm >/dev/null 2>&1; then
    return 0
  fi
  export NVM_DIR="/home/madeyskij/.nvm"
  export PNPM_HOME="/home/madeyskij/.local/share/pnpm"
  # shellcheck source=/dev/null
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  export PATH="$PNPM_HOME:$PATH"
}
setup_toolchain

if [ "${CI:-}" = "true" ]; then
  export GIT_SSH_COMMAND='ssh -o StrictHostKeyChecking=accept-new'
fi

# CI uses passwordless sudoers; manual deploy prompts once
if [ "${CI:-}" != "true" ]; then
  echo -e "${YELLOW}Requesting sudo access...${NC}"
  sudo -v
  while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &
fi

echo -e "${YELLOW}Step 1: Pulling latest changes...${NC}"
cd "$PROJECT_DIR"
git fetch origin main
git checkout main
git pull --ff-only origin main

echo -e "${YELLOW}Step 2: Building and deploying frontend...${NC}"
"$SCRIPTS_DIR/frontend_build_deploy.sh"

echo -e "${YELLOW}Step 3: Restarting backend and running migrations...${NC}"
COMPOSE_DIR="$COMPOSE_DIR" COMPOSE_FILE="$COMPOSE_FILE" "$SCRIPTS_DIR/backend_restart_migrate.sh"

echo ""
echo -e "${GREEN}Deployment complete. https://pulse-db.dev-made.it${NC}"
