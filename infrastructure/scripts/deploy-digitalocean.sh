#!/usr/bin/env bash
# ============================================================================
# Alchymine — DigitalOcean One-Click Deployment Script
#
# Provisions a fresh Ubuntu 22.04 droplet with the full Alchymine production
# stack: Docker, Nginx, Let's Encrypt SSL, PostgreSQL, Redis, FastAPI, Next.js,
# Celery, and automated backups.
#
# Usage (run ON the droplet after SSH'ing in):
#   curl -sSL https://raw.githubusercontent.com/realsammyt/Alchymine/main/infrastructure/scripts/deploy-digitalocean.sh | bash
#
#   Or clone first:
#   git clone https://github.com/realsammyt/Alchymine.git
#   cd Alchymine
#   bash infrastructure/scripts/deploy-digitalocean.sh
#
# Prerequisites:
#   - DigitalOcean Droplet (Ubuntu 22.04, 4GB+ RAM recommended)
#   - Domain DNS already pointing to droplet IP (A records for domain + www)
#   - SSH access to the droplet as root or sudo user
#
# What this script does:
#   1. Updates system packages and installs dependencies
#   2. Installs Docker Engine + Docker Compose
#   3. Configures UFW firewall (SSH, HTTP, HTTPS only)
#   4. Creates non-root deploy user
#   5. Clones or copies the Alchymine repo
#   6. Generates secure secrets (.env.production)
#   7. Obtains SSL certificate via Let's Encrypt
#   8. Starts the full production stack
#   9. Configures automated daily backups via cron
#  10. Configures unattended security updates
#
# ============================================================================
set -euo pipefail

# ── Color output helpers ─────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
step()  { echo -e "\n${GREEN}═══════════════════════════════════════════════════════${NC}"; echo -e "${GREEN}  STEP $1: $2${NC}"; echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}\n"; }

# ── Pre-flight checks ────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root. Use: sudo bash $0"
    exit 1
fi

echo ""
echo "============================================"
echo "  Alchymine — DigitalOcean Deployment"
echo "============================================"
echo ""

# ── Collect required information ─────────────────────────────────────────────
read -rp "Enter your domain name (e.g., alchymine.com): " DOMAIN
if [[ -z "$DOMAIN" ]]; then
    error "Domain name is required."
    exit 1
fi

read -rp "Enter your email for SSL certificates and alerts: " SSL_EMAIL
if [[ -z "$SSL_EMAIL" ]]; then
    error "Email is required."
    exit 1
fi

read -rsp "Enter your Anthropic API key (sk-ant-...): " ANTHROPIC_API_KEY
echo  # newline after silent input
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    warn "No Anthropic API key provided. LLM features will fall back to Ollama."
    ANTHROPIC_API_KEY=""
fi

# Confirm before proceeding
echo ""
info "Deployment configuration:"
info "  Domain:     ${DOMAIN}"
info "  Email:      ${SSL_EMAIL}"
info "  API key:    ${ANTHROPIC_API_KEY:+set (hidden)}${ANTHROPIC_API_KEY:-not set}"
echo ""
read -rp "Proceed with deployment? (y/N): " CONFIRM
if [[ "${CONFIRM,,}" != "y" ]]; then
    info "Deployment cancelled."
    exit 0
fi

DEPLOY_START=$(date +%s)

# ══════════════════════════════════════════════════════════════════════════════
step "1/10" "Updating system packages"
# ══════════════════════════════════════════════════════════════════════════════
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw \
    fail2ban \
    unattended-upgrades \
    logrotate \
    htop \
    jq
ok "System packages updated."

# ══════════════════════════════════════════════════════════════════════════════
step "2/10" "Installing Docker Engine + Compose"
# ══════════════════════════════════════════════════════════════════════════════
if command -v docker &>/dev/null; then
    ok "Docker already installed: $(docker --version)"
else
    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # Add the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ok "Docker installed: $(docker --version)"
fi

# Ensure Docker starts on boot
systemctl enable docker
systemctl start docker

# ══════════════════════════════════════════════════════════════════════════════
step "3/10" "Configuring firewall (UFW)"
# ══════════════════════════════════════════════════════════════════════════════
# Reset UFW to defaults, then only allow what we need
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# SSH — rate limit to slow brute force
ufw limit 22/tcp

# HTTP + HTTPS — required for web traffic and Let's Encrypt
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw --force enable
ok "Firewall configured: SSH (rate-limited), HTTP, HTTPS only."

# ══════════════════════════════════════════════════════════════════════════════
step "4/10" "Configuring fail2ban + SSH hardening"
# ══════════════════════════════════════════════════════════════════════════════
# Configure fail2ban for SSH brute force protection
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5
backend  = systemd

[sshd]
enabled = true
port    = ssh
filter  = sshd
maxretry = 3
bantime = 86400
EOF

systemctl enable fail2ban
systemctl restart fail2ban
ok "fail2ban configured: 3 failed SSH attempts = 24h ban."

# Harden SSH config (disable password auth if key-based access is set up)
if grep -q "^PubkeyAuthentication yes" /etc/ssh/sshd_config; then
    sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
    sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
    systemctl reload sshd
    ok "SSH hardened: password auth disabled, key-only access."
else
    warn "SSH key auth not detected. Skipping password auth disable."
    warn "Recommendation: Set up SSH keys and disable password auth manually."
fi

# ══════════════════════════════════════════════════════════════════════════════
step "5/10" "Creating deploy user + project directory"
# ══════════════════════════════════════════════════════════════════════════════
DEPLOY_USER="alchymine"
DEPLOY_HOME="/home/${DEPLOY_USER}"
APP_DIR="${DEPLOY_HOME}/Alchymine"

if id "${DEPLOY_USER}" &>/dev/null; then
    ok "User '${DEPLOY_USER}' already exists."
else
    useradd -m -s /bin/bash -G docker "${DEPLOY_USER}"
    ok "Created user '${DEPLOY_USER}' with Docker access."
fi

# Ensure user is in docker group
usermod -aG docker "${DEPLOY_USER}"

# Clone or copy repo
if [[ -d "${APP_DIR}/.git" ]]; then
    ok "Repo already cloned at ${APP_DIR}."
    cd "${APP_DIR}"
    sudo -u "${DEPLOY_USER}" git pull origin main || true
elif [[ -d "/root/Alchymine/.git" ]]; then
    info "Copying repo from /root/Alchymine..."
    cp -r /root/Alchymine "${APP_DIR}"
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_DIR}"
    ok "Repo copied to ${APP_DIR}."
else
    info "Cloning Alchymine repository..."
    sudo -u "${DEPLOY_USER}" git clone https://github.com/realsammyt/Alchymine.git "${APP_DIR}"
    ok "Repo cloned to ${APP_DIR}."
fi

cd "${APP_DIR}"

# ══════════════════════════════════════════════════════════════════════════════
step "6/10" "Generating secure production secrets"
# ══════════════════════════════════════════════════════════════════════════════
ENV_FILE="${APP_DIR}/.env.production"

if [[ -f "${ENV_FILE}" ]]; then
    warn ".env.production already exists. Backing up to .env.production.bak"
    cp "${ENV_FILE}" "${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
fi

# Generate cryptographically secure secrets
API_SECRET=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -hex 24)
REDIS_PASSWORD=$(openssl rand -hex 24)
ENCRYPTION_KEY=$(python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())")
PDF_SERVICE_TOKEN=$(openssl rand -hex 32)

cat > "${ENV_FILE}" << ENVEOF
# ============================================================================
# Alchymine — Production Environment (auto-generated $(date -u +%Y-%m-%dT%H:%M:%SZ))
# IMPORTANT: Never commit this file to version control.
# ============================================================================

# ── Domain & SSL ─────────────────────────────────────────────────────────────
DOMAIN=${DOMAIN}
SSL_EMAIL=${SSL_EMAIL}

# ── Application ──────────────────────────────────────────────────────────────
ENVIRONMENT=production
LOG_LEVEL=WARNING
ALLOWED_ORIGINS=["https://${DOMAIN}","https://www.${DOMAIN}"]

# ── API Security ─────────────────────────────────────────────────────────────
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
SIGNUP_PROMO_CODE=CHANGEME-set-your-promo-code

# ── Data Encryption ──────────────────────────────────────────────────────────
# Fernet-compatible key for column-level encryption of PII and sensitive data.
ALCHYMINE_ENCRYPTION_KEY=${ENCRYPTION_KEY}

# ── PostgreSQL ───────────────────────────────────────────────────────────────
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=alchymine
POSTGRES_USER=alchymine
POSTGRES_PASSWORD=${DB_PASSWORD}
DATABASE_URL=postgresql+asyncpg://alchymine:${DB_PASSWORD}@db:5432/alchymine

# ── Redis ────────────────────────────────────────────────────────────────────
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_CACHE_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/1

# ── Celery ───────────────────────────────────────────────────────────────────
CELERY_WORKER_CONCURRENCY=4

# ── Next.js Frontend ─────────────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=https://${DOMAIN}/api
NEXT_PUBLIC_APP_NAME=Alchymine
NEXT_PUBLIC_APP_URL=https://${DOMAIN}
WEB_PORT=3000
API_PORT=8000

# ── Claude API ───────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514

# ── PDF Service ──────────────────────────────────────────────────────────────
# Shared bearer token used by the API/worker to authenticate with the PDF service.
# Generated automatically during deployment — never share or commit this value.
PDF_SERVICE_TOKEN=${PDF_SERVICE_TOKEN}
PDF_SERVICE_URL=http://pdf-service:3001

# ── Backup ───────────────────────────────────────────────────────────────────
BACKUP_RETENTION=30
ENVEOF

# Secure the env file
chmod 600 "${ENV_FILE}"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "${ENV_FILE}"
ok "Production secrets generated and saved to .env.production"
ok "File permissions set to 600 (owner read/write only)."

# ══════════════════════════════════════════════════════════════════════════════
step "7/10" "Obtaining SSL certificate (Let's Encrypt)"
# ══════════════════════════════════════════════════════════════════════════════
info "Requesting SSL certificate for ${DOMAIN} and www.${DOMAIN}..."
info "Make sure your DNS A records point to this server's IP address."
echo ""

# Use the existing init-ssl.sh script
cd "${APP_DIR}/infrastructure/scripts"
chmod +x init-ssl.sh
bash init-ssl.sh

cd "${APP_DIR}"
ok "SSL certificate obtained."

# ══════════════════════════════════════════════════════════════════════════════
step "8/10" "Building and starting production stack"
# ══════════════════════════════════════════════════════════════════════════════
cd "${APP_DIR}/infrastructure"

info "Building Docker images (this may take 5-10 minutes on first run)..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

info "Starting all services..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Wait for health checks to pass
info "Waiting for services to become healthy..."
MAX_WAIT=120
ELAPSED=0
while [[ $ELAPSED -lt $MAX_WAIT ]]; do
    HEALTHY=$(docker compose -f docker-compose.yml -f docker-compose.prod.yml ps --format json 2>/dev/null | jq -s '[.[] | select(.Health == "healthy")] | length' 2>/dev/null || echo "0")
    TOTAL=$(docker compose -f docker-compose.yml -f docker-compose.prod.yml ps --format json 2>/dev/null | jq -s 'length' 2>/dev/null || echo "0")

    if [[ "$HEALTHY" -ge 5 ]]; then
        break
    fi

    echo -ne "\r   Healthy: ${HEALTHY}/${TOTAL} services (${ELAPSED}s elapsed)..."
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done
echo ""

# Show final status
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
ok "Production stack is running."

cd "${APP_DIR}"

# ══════════════════════════════════════════════════════════════════════════════
step "9/10" "Setting up automated backups"
# ══════════════════════════════════════════════════════════════════════════════
BACKUP_DIR="${APP_DIR}/backups"
mkdir -p "${BACKUP_DIR}"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "${BACKUP_DIR}"

# Make backup script executable
chmod +x "${APP_DIR}/infrastructure/scripts/backup-db.sh"

# Add daily backup cron job (runs at 3:00 AM server time)
CRON_LINE="0 3 * * * cd ${APP_DIR} && bash infrastructure/scripts/backup-db.sh ${BACKUP_DIR} >> ${BACKUP_DIR}/backup.log 2>&1"

# Install cron job for deploy user (avoid duplicates)
(crontab -u "${DEPLOY_USER}" -l 2>/dev/null | grep -v "backup-db.sh" ; echo "${CRON_LINE}") | crontab -u "${DEPLOY_USER}" -
ok "Daily database backup scheduled at 3:00 AM → ${BACKUP_DIR}"

# ══════════════════════════════════════════════════════════════════════════════
step "10/10" "Enabling unattended security updates"
# ══════════════════════════════════════════════════════════════════════════════
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

systemctl enable unattended-upgrades
systemctl restart unattended-upgrades
ok "Unattended security updates enabled."

# ══════════════════════════════════════════════════════════════════════════════
# Final Summary
# ══════════════════════════════════════════════════════════════════════════════
DEPLOY_END=$(date +%s)
DEPLOY_DURATION=$(( DEPLOY_END - DEPLOY_START ))

echo ""
echo "============================================"
echo "  Alchymine Deployment Complete!"
echo "============================================"
echo ""
echo "  Domain:       https://${DOMAIN}"
echo "  Time:         ${DEPLOY_DURATION} seconds"
echo "  Deploy user:  ${DEPLOY_USER}"
echo "  App dir:      ${APP_DIR}"
echo "  Backups:      ${BACKUP_DIR} (daily at 3 AM)"
echo ""
echo "  Services running:"
echo "    - Nginx      (reverse proxy + SSL)"
echo "    - FastAPI    (4 workers)"
echo "    - Next.js    (production build)"
echo "    - Celery     (4 workers)"
echo "    - PostgreSQL (tuned for production)"
echo "    - Redis      (AOF + RDB persistence)"
echo "    - Certbot    (auto-renewal every 12h)"
echo "    - PDF        (Puppeteer, internal-only network)"
echo ""
echo "  Security:"
echo "    - UFW firewall (SSH, HTTP, HTTPS only)"
echo "    - fail2ban (SSH brute force protection)"
echo "    - SSL/TLS 1.2+ (Let's Encrypt)"
echo "    - Non-root deploy user"
echo "    - Unattended security updates"
echo "    - .env.production: chmod 600"
echo ""
echo "  Useful commands (run as ${DEPLOY_USER}):"
echo "    su - ${DEPLOY_USER}"
echo "    cd ${APP_DIR}/infrastructure"
echo ""
echo "    # View logs"
echo "    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
echo ""
echo "    # Restart services"
echo "    docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"
echo ""
echo "    # Check service health"
echo "    docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
echo ""
echo "    # Manual backup"
echo "    bash ../infrastructure/scripts/backup-db.sh ../backups"
echo ""
echo "  Next steps:"
echo "    1. Verify: curl -I https://${DOMAIN}"
echo "    2. Set up Cloudflare (see docs/guides/deployment-guide.md)"
echo "    3. Test the application in your browser"
echo ""
echo "============================================"
