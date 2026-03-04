#!/usr/bin/env bash
# ============================================================================
# Alchymine — Zero-Downtime Deploy with Automatic Rollback
#
# Pulls pre-built GHCR images, starts temporary containers alongside the
# existing stack, health-checks them, then swaps nginx. If anything fails,
# the old version keeps serving.
#
# Usage: deploy-zero-downtime.sh <version>
#   e.g. deploy-zero-downtime.sh 0.5.0
# ============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

VERSION="${1:?Usage: deploy-zero-downtime.sh <version>}"

APP_DIR="/home/alchymine/Alchymine"
INFRA_DIR="${APP_DIR}/infrastructure"
NGINX_CONF="${INFRA_DIR}/nginx/nginx.conf"
NGINX_CONF_BAK="${NGINX_CONF}.deploy-bak"
ENV_FILE="${APP_DIR}/.env.production"

DEPLOY_LOG_DIR="${APP_DIR}/deploys"
LOG_FILE="${DEPLOY_LOG_DIR}/deploy-${VERSION}-$(date +%Y%m%d-%H%M%S).log"

VERSION_FILE="${APP_DIR}/.deployed-version"
PREV_VERSION_FILE="${APP_DIR}/.previous-version"

IMAGE_PREFIX="ghcr.io/realsammyt/alchymine"

DC="docker compose --env-file ${ENV_FILE} \
  -f ${INFRA_DIR}/docker-compose.yml \
  -f ${INFRA_DIR}/docker-compose.prod.yml \
  -f ${INFRA_DIR}/docker-compose.deploy.yml"

# ── State tracking for rollback ──────────────────────────────────────────────

PHASE="init"
TEMPS_RUNNING=false
NGINX_SWAPPED=false
COMPOSE_RECREATED=false

# ── Logging ──────────────────────────────────────────────────────────────────

mkdir -p "$DEPLOY_LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
err()  { echo "[$(date '+%H:%M:%S')] ERROR: $*" >&2; }

# ── Rollback on failure ─────────────────────────────────────────────────────

rollback() {
  local exit_code=$?
  err "Deploy failed at phase '${PHASE}' (exit ${exit_code})"

  if $COMPOSE_RECREATED && $NGINX_SWAPPED; then
    # Compose tore down old containers and nginx points at temps.
    # Temps are the only thing serving — do NOT remove them or restore nginx.
    err "Compose was recreated but deploy did not complete."
    err "Temp containers are serving traffic. DO NOT remove them."
    err "To finish: re-run 'deploy-zero-downtime.sh ${VERSION}'"
    err "To rollback manually: restore nginx.conf from .deploy-bak and bring up old images."
    exit "$exit_code"
  fi

  # Restore nginx config if we swapped it (safe: old compose containers still exist)
  if $NGINX_SWAPPED && [ -f "$NGINX_CONF_BAK" ]; then
    log "Restoring original nginx config..."
    cp "$NGINX_CONF_BAK" "$NGINX_CONF"
    docker exec alchymine-nginx nginx -s reload 2>/dev/null || true
    log "Nginx restored to original config"
  fi

  # Remove temp containers (old compose containers are still serving)
  if $TEMPS_RUNNING; then
    log "Removing temp containers..."
    docker rm -f alchymine-api-tmp alchymine-web-tmp 2>/dev/null || true
    TEMPS_RUNNING=false
    log "Temp containers removed"
  fi

  rm -f "$NGINX_CONF_BAK"
  log "Rollback complete. Old version should still be serving."
  exit "$exit_code"
}

trap rollback ERR

# ── Pre-flight cleanup ───────────────────────────────────────────────────────
# Remove leftover temp containers from a previous failed deploy
docker rm -f alchymine-api-tmp alchymine-web-tmp 2>/dev/null || true

# ── Main deploy sequence ────────────────────────────────────────────────────

log "=========================================="
log "Starting zero-downtime deploy of v${VERSION}"
log "=========================================="

# Save previous version for rollback
if [ -f "$VERSION_FILE" ]; then
  cp "$VERSION_FILE" "$PREV_VERSION_FILE"
  log "Previous version: $(cat "$PREV_VERSION_FILE")"
fi

# ── Step 1: Pull GHCR images ────────────────────────────────────────────────
PHASE="pull"
log "Step 1/7: Pulling GHCR images..."

for svc in api web worker pdf; do
  log "  Pulling ${IMAGE_PREFIX}-${svc}:${VERSION}..."
  docker pull "${IMAGE_PREFIX}-${svc}:${VERSION}"
done

log "All images pulled successfully"

# ── Step 2: Start temporary containers ───────────────────────────────────────
PHASE="start-temps"
log "Step 2/7: Starting temp containers..."

# Source env vars for constructing service URLs
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

# Temp API — connected to alchymine-net so it can reach db/redis via compose DNS
docker run -d \
  --name alchymine-api-tmp \
  --network alchymine-net \
  --env-file "$ENV_FILE" \
  -e "DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-alchymine}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-alchymine}" \
  -e "REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0" \
  -e "REDIS_CACHE_URL=redis://:${REDIS_PASSWORD}@redis:6379/1" \
  -e "CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0" \
  -e "CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/1" \
  -e "ENVIRONMENT=production" \
  -e "LOG_LEVEL=WARNING" \
  -e "PDF_SERVICE_URL=http://pdf-service:3001" \
  "${IMAGE_PREFIX}-api:${VERSION}" \
  uvicorn alchymine.api.main:app \
    --host 0.0.0.0 --port 8000 \
    --workers 4 --loop uvloop --http httptools \
    --log-level warning --access-log

# Connect temp API to pdf-net so it can reach pdf-service during swap window
docker network connect alchymine-pdf-net alchymine-api-tmp

# Temp Web — NEXT_PUBLIC_API_URL is baked at build time as "" (relative URLs via nginx)
docker run -d \
  --name alchymine-web-tmp \
  --network alchymine-net \
  -e "NODE_ENV=production" \
  "${IMAGE_PREFIX}-web:${VERSION}"

TEMPS_RUNNING=true
log "Temp containers started"

# ── Step 3: Health-check temp containers ─────────────────────────────────────
PHASE="health-check-temps"
log "Step 3/7: Health-checking temp containers..."

# API health check — max 60s
for i in $(seq 1 30); do
  if docker exec alchymine-api-tmp \
    python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    2>/dev/null; then
    log "  Temp API is healthy"
    break
  fi
  if [ "$i" = "30" ]; then
    err "Temp API failed health check after 60s"
    docker logs --tail=30 alchymine-api-tmp 2>&1 || true
    false  # triggers ERR trap for rollback
  fi
  sleep 2
done

# Web health check — max 40s
for i in $(seq 1 20); do
  if docker exec alchymine-web-tmp \
    node -e "require('http').get('http://localhost:3000/api/health', (r) => { process.exit(r.statusCode === 200 ? 0 : 1) }).on('error', () => process.exit(1))" \
    2>/dev/null; then
    log "  Temp web is healthy"
    break
  fi
  if [ "$i" = "20" ]; then
    err "Temp web failed health check after 40s"
    docker logs --tail=30 alchymine-web-tmp 2>&1 || true
    false  # triggers ERR trap for rollback
  fi
  sleep 2
done

log "All temp containers healthy"

# ── Step 4: Swap nginx to temp containers ────────────────────────────────────
PHASE="nginx-swap-to-temps"
log "Step 4/7: Swapping nginx to temp containers..."

cp "$NGINX_CONF" "$NGINX_CONF_BAK"
sed -i 's/server web:3000/server alchymine-web-tmp:3000/' "$NGINX_CONF"
sed -i 's/server api:8000/server alchymine-api-tmp:8000/' "$NGINX_CONF"

# Verify sed replacements actually occurred
grep -q 'server alchymine-web-tmp:3000' "$NGINX_CONF" || {
  err "sed replacement for web upstream failed — nginx.conf format may have changed"
  cp "$NGINX_CONF_BAK" "$NGINX_CONF"
  false
}
grep -q 'server alchymine-api-tmp:8000' "$NGINX_CONF" || {
  err "sed replacement for api upstream failed — nginx.conf format may have changed"
  cp "$NGINX_CONF_BAK" "$NGINX_CONF"
  false
}

if docker exec alchymine-nginx nginx -t 2>&1; then
  docker exec alchymine-nginx nginx -s reload
  NGINX_SWAPPED=true
  log "Nginx now routing to temp containers"
else
  err "Nginx config test failed — restoring original"
  cp "$NGINX_CONF_BAK" "$NGINX_CONF"
  false  # triggers ERR trap for rollback
fi

# ── Step 5: Recreate compose services with new images ────────────────────────
PHASE="compose-recreate"
log "Step 5/7: Recreating compose services with new images..."

export DEPLOY_VERSION="${VERSION}"
$DC up -d --no-deps --no-build --force-recreate api web worker pdf-service
COMPOSE_RECREATED=true

# Wait for compose containers to become healthy (max 90s)
log "Waiting for compose containers to become healthy..."
for i in $(seq 1 45); do
  API_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' alchymine-api 2>/dev/null || echo "starting")
  WEB_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' alchymine-web 2>/dev/null || echo "starting")

  if [ "$API_HEALTH" = "healthy" ] && [ "$WEB_HEALTH" = "healthy" ]; then
    log "  Compose containers are healthy (api=$API_HEALTH, web=$WEB_HEALTH)"
    break
  fi

  if [ "$i" = "45" ]; then
    err "Compose containers not healthy after 90s (api=$API_HEALTH, web=$WEB_HEALTH)"
    err "Temp containers are still serving traffic via nginx."
    err "Run 'deploy-zero-downtime.sh ${VERSION}' again or fix manually."
    false  # triggers ERR trap (temps kept alive since COMPOSE_RECREATED=true)
  fi

  # Log progress every 10s
  if [ "$((i % 5))" = "0" ]; then
    log "  Waiting... api=$API_HEALTH web=$WEB_HEALTH ($((i * 2))s / 90s)"
  fi
  sleep 2
done

# ── Step 6: Swap nginx back to compose services ─────────────────────────────
PHASE="nginx-swap-to-compose"
log "Step 6/7: Swapping nginx back to compose services..."

cp "$NGINX_CONF_BAK" "$NGINX_CONF"

if docker exec alchymine-nginx nginx -t 2>&1; then
  docker exec alchymine-nginx nginx -s reload
  NGINX_SWAPPED=false
  log "Nginx now routing to compose services"
else
  err "Nginx config test failed on restore — temp containers still serving"
  err "Manual fix: copy nginx.conf.deploy-bak over nginx.conf and reload"
  false  # triggers ERR trap
fi

# ── Step 7: Cleanup ─────────────────────────────────────────────────────────
PHASE="cleanup"
log "Step 7/7: Cleanup..."

docker rm -f alchymine-api-tmp alchymine-web-tmp 2>/dev/null || true
TEMPS_RUNNING=false

rm -f "$NGINX_CONF_BAK"
docker image prune -f

echo "${VERSION}" > "$VERSION_FILE"

log "=========================================="
log "Deploy complete: v${VERSION} is live"
log "=========================================="
