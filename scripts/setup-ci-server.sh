#!/usr/bin/env bash
# One-time VPS setup for GitHub Actions deploy (pulse-db).
# Run on the server as a user with sudo: bash scripts/setup-ci-server.sh

set -euo pipefail

PROJECT_USER="${PROJECT_USER:-madeyskij}"
PROJECT_DIR="/home/${PROJECT_USER}/projects/pulse-db"
DEPLOY_DIR="/var/www/pulse-db/dist"
WWW_PARENT="/var/www/pulse-db"

echo "==> Groups"
sudo groupadd -f deploy
sudo usermod -aG docker,caddy,deploy deploy
sudo usermod -aG deploy "$PROJECT_USER"

echo "==> Project permissions"
sudo chown -R "${PROJECT_USER}:deploy" "$PROJECT_DIR"
sudo chmod -R g+rwX "$PROJECT_DIR"
sudo find "$PROJECT_DIR" -type d -exec chmod g+s {} \;

echo "==> Frontend deploy dir"
sudo mkdir -p "$DEPLOY_DIR"
sudo chown -R caddy:deploy "$WWW_PARENT"
sudo chmod -R 775 "$WWW_PARENT"
sudo find "$WWW_PARENT" -type d -exec chmod g+s {} \;

echo "==> Sudoers"
sudo tee /etc/sudoers.d/pulse-db-deploy > /dev/null <<EOF
deploy ALL=(ALL) NOPASSWD: /bin/rm -rf /var/www/pulse-db/dist/*
deploy ALL=(ALL) NOPASSWD: /bin/cp -r * /var/www/pulse-db/dist/
deploy ALL=(ALL) NOPASSWD: /usr/bin/chown -R caddy\:deploy /var/www/pulse-db/dist
deploy ALL=(ALL) NOPASSWD: /usr/bin/mkdir -p /var/www/pulse-db/dist
deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload caddy
${PROJECT_USER} ALL=(deploy) NOPASSWD: ${PROJECT_DIR}/scripts/frontend_pnpm_build.sh
EOF
sudo chmod 440 /etc/sudoers.d/pulse-db-deploy
sudo visudo -c -f /etc/sudoers.d/pulse-db-deploy

echo "==> SSH keys for deploy user"
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chown deploy:deploy /home/deploy/.ssh

if [ ! -f /home/deploy/.ssh/id_ed25519 ]; then
  sudo -u deploy ssh-keygen -t ed25519 -C "github-actions-pulse-db" -f /home/deploy/.ssh/id_ed25519 -N ""
fi
if [ ! -f /home/deploy/.ssh/id_ed25519_github ]; then
  sudo -u deploy ssh-keygen -t ed25519 -C "deploy-git-pulse-db" -f /home/deploy/.ssh/id_ed25519_github -N ""
fi

PUB=$(sudo cat /home/deploy/.ssh/id_ed25519.pub)
if ! sudo grep -qF "$PUB" /home/deploy/.ssh/authorized_keys 2>/dev/null; then
  echo "$PUB" | sudo tee -a /home/deploy/.ssh/authorized_keys > /dev/null
fi

sudo -u deploy tee /home/deploy/.ssh/config > /dev/null <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
EOF

echo 'github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dhXl9GJL' | sudo tee /home/deploy/.ssh/known_hosts > /dev/null
sudo chmod 600 /home/deploy/.ssh/authorized_keys /home/deploy/.ssh/config
sudo chmod 644 /home/deploy/.ssh/known_hosts
sudo chown -R deploy:deploy /home/deploy/.ssh

sudo -u deploy git config --global --add safe.directory "$PROJECT_DIR"

echo ""
echo "Done. Add to GitHub repo jm-sky/pulse-db:"
echo "  Secrets: VPS_HOST, VPS_USER=deploy, VPS_SSH_KEY (private key below), VPS_PROJECT_PATH=${PROJECT_DIR}"
echo "  Deploy key (read-only):"
sudo cat /home/deploy/.ssh/id_ed25519_github.pub
echo ""
echo "VPS_SSH_KEY private key:"
sudo cat /home/deploy/.ssh/id_ed25519
