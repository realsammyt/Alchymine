#!/usr/bin/env bash
# ============================================================================
# Alchymine — Initial SSL Certificate Setup (Let's Encrypt via Certbot)
# Obtains the first SSL certificate for alchymine.com.
#
# Prerequisites:
#   - DNS A records for alchymine.com and www.alchymine.com pointing to this server
#   - Docker and docker compose installed
#   - Port 80 open and accessible from the internet
#   - .env.production file with SSL_EMAIL and DOMAIN set
#
# Usage:
#   ./init-ssl.sh                # Production certificate
#   ./init-ssl.sh --staging      # Staging certificate (for testing)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
INFRA_DIR="${SCRIPT_DIR}/.."

# ── Load configuration ──────────────────────────────────────────────────────
if [ -f "${PROJECT_ROOT}/.env.production" ]; then
    # shellcheck source=/dev/null
    source "${PROJECT_ROOT}/.env.production"
fi

DOMAIN="${DOMAIN:-alchymine.com}"
SSL_EMAIL="${SSL_EMAIL:?ERROR: SSL_EMAIL must be set in .env.production}"
STAGING_FLAG=""

if [ "${1:-}" = "--staging" ]; then
    STAGING_FLAG="--staging"
    echo "*** STAGING MODE — certificate will NOT be trusted by browsers ***"
    echo ""
fi

echo "=== Alchymine SSL Certificate Setup ==="
echo "Domain:  ${DOMAIN}"
echo "Email:   ${SSL_EMAIL}"
echo "Mode:    ${STAGING_FLAG:-production}"
echo ""

# ── Step 1: Create required directories and volumes ──────────────────────────
echo "[1/4] Creating certificate directories..."
docker volume create alchymine-certbot-webroot 2>/dev/null || true
docker volume create alchymine-certbot-certs 2>/dev/null || true

# ── Step 2: Start nginx with HTTP-only config for ACME challenge ────────────
echo "[2/4] Starting nginx for ACME challenge..."

# Create a temporary nginx config that only serves HTTP (for initial cert)
TEMP_CONF=$(mktemp)
cat > "${TEMP_CONF}" << 'NGINX_CONF'
events { worker_connections 1024; }
http {
    server {
        listen 80;
        server_name _;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
            allow all;
        }

        location / {
            return 200 "Waiting for SSL setup...";
            add_header Content-Type text/plain;
        }
    }
}
NGINX_CONF

# Start a temporary nginx container for the ACME challenge
docker run -d \
    --name alchymine-nginx-init \
    -p 80:80 \
    -v alchymine-certbot-webroot:/var/www/certbot \
    -v "${TEMP_CONF}:/etc/nginx/nginx.conf:ro" \
    nginx:1.25-alpine \
|| { echo "ERROR: Failed to start nginx. Is port 80 in use?"; rm -f "${TEMP_CONF}"; exit 1; }

echo "   nginx started on port 80."

# ── Step 3: Request certificate from Let's Encrypt ──────────────────────────
echo "[3/4] Requesting certificate from Let's Encrypt..."
echo "   (This may take 30-60 seconds...)"

docker run --rm \
    -v alchymine-certbot-certs:/etc/letsencrypt \
    -v alchymine-certbot-webroot:/var/www/certbot \
    certbot/certbot:latest \
    certonly \
    --webroot \
    -w /var/www/certbot \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}" \
    --email "${SSL_EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    ${STAGING_FLAG}

CERTBOT_EXIT=$?

# ── Step 4: Cleanup temporary nginx ─────────────────────────────────────────
echo "[4/4] Cleaning up..."
docker stop alchymine-nginx-init 2>/dev/null || true
docker rm alchymine-nginx-init 2>/dev/null || true
rm -f "${TEMP_CONF}"

# ── Result ───────────────────────────────────────────────────────────────────
echo ""
if [ ${CERTBOT_EXIT} -eq 0 ]; then
    echo "=== SSL certificate obtained successfully ==="
    echo ""
    echo "Certificate files are stored in Docker volume 'alchymine-certbot-certs'."
    echo ""
    echo "Next steps:"
    echo "  1. Start the full production stack:"
    echo "     cd ${INFRA_DIR}"
    echo "     docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
    echo ""
    echo "  2. Verify HTTPS is working:"
    echo "     curl -I https://${DOMAIN}"
    echo ""
    echo "  3. Auto-renewal is handled by the certbot service in docker-compose.prod.yml."
else
    echo "=== ERROR: Certificate request failed ==="
    echo ""
    echo "Common issues:"
    echo "  - DNS A records not pointing to this server"
    echo "  - Port 80 blocked by firewall"
    echo "  - Rate limit exceeded (use --staging for testing)"
    echo ""
    echo "Try again with staging mode first: $0 --staging"
    exit 1
fi
