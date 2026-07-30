#!/usr/bin/env bash
# Build Vue frontend and deploy to /var/www/pulse-db/dist.
# Called by deploy.sh — can also be run standalone from the project root.
#
# Always runs the pnpm build as the `deploy` OS user so node_modules/.pnpm-store
# ownership never splits between CI (`deploy`) and manual deploys.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
DEPLOY_DIR="/var/www/pulse-db/dist"

echo -e "${GREEN}Building frontend...${NC}"

echo -e "${YELLOW}Installing dependencies and building...${NC}"
if [ "$(whoami)" = "deploy" ]; then
  "$SCRIPTS_DIR/frontend_pnpm_build.sh"
else
  sudo -u deploy "$SCRIPTS_DIR/frontend_pnpm_build.sh"
fi

echo -e "${YELLOW}Deploying to $DEPLOY_DIR...${NC}"

deploy_frontend() {
  mkdir -p "$DEPLOY_DIR"
  rm -rf "${DEPLOY_DIR:?}"/*
  cp -r dist/* "$DEPLOY_DIR/"
}

if [ -w "$(dirname "$DEPLOY_DIR")" ] || [ -w "$DEPLOY_DIR" ]; then
  deploy_frontend
else
  sudo mkdir -p "$DEPLOY_DIR"
  sudo rm -rf "${DEPLOY_DIR:?}"/*
  sudo cp -r dist/* "$DEPLOY_DIR/"
fi

sudo chown -R caddy:deploy "$DEPLOY_DIR"

echo -e "${GREEN}Frontend deployed to $DEPLOY_DIR${NC}"
