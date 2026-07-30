# Deployment Setup Guide

This guide explains how to set up and deploy the PulseDB application with support for both manual deployment (main user) and automated GitHub Actions deployment (`deploy` user).

## Overview

- **Project folder (git repository):** `/home/$USER/projects/pulse-db/`
- **Deployment folder (Caddy serves from):** `/var/www/pulse-db/`
- **Users with deploy access:**
  - Main user (your username) - manual deployment
  - `deploy` - GitHub Actions automated deployment

Both users should be members of the `docker`, `caddy`, and `deploy` groups.

## Initial Setup

### 1. Configure Permissions and Groups

You need to configure permissions for both users. Run these commands as root or with sudo:

```bash
# Configuration variables - REPLACE WITH YOUR USERNAME
PROJECT_USER="your-username"
PROJECT_DIR="/home/$PROJECT_USER/projects/pulse-db"
DEPLOY_DIR="/var/www/pulse-db"

# Create deploy user if it doesn't exist
sudo useradd -m -s /bin/bash deploy

# Add both users to required groups
sudo usermod -a -G docker,caddy,deploy $PROJECT_USER
sudo usermod -a -G docker,caddy deploy

# Create deploy group and add both users
sudo groupadd -f deploy
sudo usermod -a -G deploy $PROJECT_USER
sudo usermod -a -G deploy deploy

# Set project directory permissions
sudo chown -R $PROJECT_USER:deploy "$PROJECT_DIR"
sudo chmod -R g+rwX "$PROJECT_DIR"
sudo chmod g+s "$PROJECT_DIR"

# Set deployment directory permissions
sudo mkdir -p "$DEPLOY_DIR"
sudo chown -R caddy:deploy "$DEPLOY_DIR"
sudo chmod -R 775 "$DEPLOY_DIR"
sudo chmod g+s "$DEPLOY_DIR"
```

### 2. Configure Sudoers

Create a sudoers file to allow passwordless deployment commands:

```bash
# Create sudoers file
sudo tee /etc/sudoers.d/pulse-db-deploy > /dev/null <<'EOF'
# PulseDB Deployment Permissions
# Replace YOUR_USERNAME with your actual username

# Both users can manage files in /var/www/pulse-db
YOUR_USERNAME ALL=(ALL) NOPASSWD: /bin/rm -rf /var/www/pulse-db/*, /bin/cp -r * /var/www/pulse-db/, /usr/bin/chown -R caddy\:deploy /var/www/pulse-db
deploy ALL=(ALL) NOPASSWD: /bin/rm -rf /var/www/pulse-db/*, /bin/cp -r * /var/www/pulse-db/, /usr/bin/chown -R caddy\:deploy /var/www/pulse-db

# Both users can reload Caddy (if needed)
YOUR_USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload caddy
deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload caddy
EOF

# Set correct permissions and validate
sudo chmod 440 /etc/sudoers.d/pulse-db-deploy
sudo visudo -c -f /etc/sudoers.d/pulse-db-deploy
```

**Important:** Replace `YOUR_USERNAME` in the sudoers file with your actual username before saving. After running these commands, log out and log back in for group changes to take effect.

### 3. Set Up SSH Key for GitHub Actions

The `deploy` user needs an SSH key for GitHub Actions to authenticate:

```bash
# Switch to deploy user
sudo su - deploy

# Generate SSH key (if not already exists)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/id_ed25519

# Display the private key (you'll add this to GitHub Secrets)
cat ~/.ssh/id_ed25519

# Add the public key to authorized_keys
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Exit deploy user
exit
```

### 4. Configure GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `DEPLOY_HOST` - Your server's IP address or hostname
- `DEPLOY_SSH_KEY` - The **private key** from `/home/deploy/.ssh/id_ed25519`
- `DEPLOY_PORT` - SSH port (optional, defaults to 22)

To add the SSH key secret:
1. Copy the entire contents of the private key file (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`)
2. Paste it into the GitHub secret value field

## Manual Deployment

One deploy script auto-detects the active Docker Compose stack:

- `scripts/deploy.sh` — detects compose from the running `pulse-db-app` container,
  or defaults to prod (`docker-compose.yml` in repo root) when no container is running.

```bash
cd /home/$USER/projects/pulse-db
bash scripts/deploy.sh              # auto-detect (or prod default)
bash scripts/deploy.sh --prod       # force root docker-compose.yml
bash scripts/deploy.sh --dev        # force docker-compose.dev.yml (repo root)
```

The former `scripts/deploy_dev.sh` has been removed; use `bash scripts/deploy.sh` instead
(it will detect a dev stack automatically when that container is running).

The script will:
1. Pull latest changes from git
2. Install frontend dependencies with pnpm
3. Build the frontend
4. Deploy to `/var/www/pulse-db/dist`
5. Rebuild and force-recreate the backend app container, then run migrations

**Important:** always rebuild and `--force-recreate` the `app` container after a `git
pull`, even for the bind-mounted dev compose file — the process doesn't hot-reload
in the prod Dockerfile, and a plain `docker compose up -d` is a no-op when the compose
config hasn't changed, so the old code keeps running in memory despite the new files
being on disk and migrations having applied.

## Automated Deployment (GitHub Actions)

The GitHub Actions workflow (`.github/workflows/deploy.yml`) automatically deploys when:
- Code is pushed to the `main` branch
- Manually triggered via GitHub Actions UI (workflow_dispatch)

### Workflow Steps

1. **Lint and Type Check** (runs in GitHub runner)
   - Checkout code
   - Install dependencies
   - Run `pnpm lint`
   - Run `pnpm type-check`

2. **Deploy** (runs on your server via SSH)
   - Connect to server as `deploy` user
   - Run `scripts/deploy.sh` (auto-detects the active compose stack on the server)

The workflow will fail if linting or type checking fails, preventing broken code from being deployed.

## Deployment Script Details

`scripts/deploy.sh` performs:

1. **Resolve compose context** — auto-detect from running container, or `--prod` / `--dev`
2. **Pull latest changes** - `git pull`
3. **Install dependencies** - `pnpm install --frozen-lockfile`
4. **Build frontend** - `pnpm build`
5. **Deploy to /var/www/pulse-db/dist**
   - Remove old files: `sudo rm -rf /var/www/pulse-db/dist/*`
   - Copy new build: `sudo cp -r dist/* /var/www/pulse-db/dist/`
   - Fix ownership: `sudo chown -R caddy:deploy /var/www/pulse-db/dist`
6. **Restart backend and migrate** (via `scripts/backend_restart_migrate.sh`)
   - Build the app image: `docker compose -f <compose-file> build app`
   - Force-recreate the container: `docker compose -f <compose-file> up -d --force-recreate app`
   - Run migrations: `docker compose -f <compose-file> exec app python -m cli db migrate`

Compose selection:

| Mode | Compose file | Working directory |
|------|--------------|-------------------|
| Auto-detect (container running) | From container labels | From container labels |
| Default (no container) | `docker-compose.yml` | repo root |
| `--prod` | `docker-compose.yml` | repo root |
| `--dev` | `docker-compose.dev.yml` | `backend/` |

Shared detection logic lives in `scripts/lib/detect_compose.sh` (also used by `exec.sh`).

## Permission Structure

### Project Directory (`/home/$USER/projects/pulse-db/`)
- Owner: `your-username:deploy`
- Permissions: `g+rwX` (group read, write, execute)
- SGID bit set: new files inherit `deploy` group

### Deployment Directory (`/var/www/pulse-db/`)
- Owner: `caddy:deploy`
- Permissions: `775` (owner/group full, others read+execute)
- SGID bit set: new files inherit `deploy` group

### Sudoers Configuration (`/etc/sudoers.d/pulse-db-deploy`)

Both your main user and `deploy` can run these commands without password:
- `sudo rm -rf /var/www/pulse-db/*`
- `sudo cp -r * /var/www/pulse-db/`
- `sudo chown -R caddy:deploy /var/www/pulse-db`
- `sudo systemctl reload caddy`

### Docker Access

Both users are in the `docker` group, allowing them to run Docker commands without `sudo`.

## Troubleshooting

### "Permission denied" when deploying
- Ensure you've run the permission setup commands from section 1
- Log out and log back in to refresh group memberships
- Check group membership: `groups` (should include `docker`, `caddy`, `deploy`)

### GitHub Actions fails with SSH connection error
- Verify the `DEPLOY_HOST` secret is correct
- Verify the `DEPLOY_SSH_KEY` secret contains the complete private key
- Test SSH connection: `ssh deploy@YOUR_HOST` from your local machine

### GitHub Actions fails with "git pull" error
- Ensure the `deploy` user has read access to the git repository
- The project directory should be readable by the `deploy` group

### Frontend not updating after deployment
- Check Caddy is serving from `/var/www/pulse-db/`
- Verify files were copied: `ls -la /var/www/pulse-db/`
- Hard refresh browser (Ctrl+Shift+R) to clear cache

### Docker commands fail
- Ensure user is in `docker` group: `groups`
- Restart Docker service: `sudo systemctl restart docker`
- Log out and log back in to refresh group memberships

## Security Notes

- The `deploy` user has limited sudo access (only specific commands via sudoers)
- SSH key for `deploy` should be kept secure and only used for GitHub Actions
- The sudoers configuration is validated with `visudo -c` during setup
- Both users can only manage files in `/var/www/pulse-db/`, not system-wide

## Manual Commands

### Check deployment status
```bash
# Check Caddy status
sudo systemctl status caddy

# Check backend containers
cd /home/$USER/projects/pulse-db/backend
docker compose -f docker-compose.dev.yml ps

# Check deployed frontend
ls -la /var/www/pulse-db/
```

### Reload Caddy configuration
```bash
sudo systemctl reload caddy
```

### Configure Cache Headers for Static Assets

To improve Lighthouse performance scores, configure cache headers in your Caddyfile. See `docs/Caddyfile.example` for a complete example.

Key points:
- **Hashed assets** (`/assets/*.js`, `/assets/*.css`): Cache for 1 year (`max-age=31536000, immutable`)
- **Other static files**: Cache for 1 hour (`max-age=3600`)
- **HTML files**: No cache (always fresh)

The FastAPI backend also adds cache headers as a fallback, but Caddy configuration is recommended for optimal performance.

### View deployment logs
```bash
# Frontend build logs (during manual deployment)
# Output is shown directly in terminal

# Backend logs
cd /home/$USER/projects/pulse-db/backend
docker compose -f docker-compose.dev.yml logs -f
```
