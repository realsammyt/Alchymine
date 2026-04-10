#!/usr/bin/env bash
# Reset the local dev DB and re-seed with a dev user + invite code.
# Used when switching between feature branches that have conflicting migrations
# (e.g., Track 2 chat_messages 0012 vs Track 3 generated_images 0012).
#
# Usage: scripts/reset-dev-db.sh
#
# After running: log in at http://localhost:3200/login with dev@example.com / devpassword123

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "==> Stopping db + dropping volume"
docker compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.dev.yml --env-file .secrets/.env stop db
docker compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.dev.yml --env-file .secrets/.env rm -f db
docker volume rm alchymine-db-data 2>/dev/null || true

echo "==> Starting fresh db"
docker compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.dev.yml --env-file .secrets/.env up -d db
sleep 3

echo "==> Restarting api so alembic can run against fresh db"
docker compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.dev.yml --env-file .secrets/.env restart api

echo "==> Waiting for api to be healthy"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf http://localhost:8200/health >/dev/null 2>&1; then
    echo "    api ready"
    break
  fi
  sleep 2
done

echo "==> Running alembic upgrade head"
MSYS_NO_PATHCONV=1 docker exec -w /app alchymine-api alembic upgrade head

echo "==> Seeding invite code DEVLOCAL"
docker exec -i alchymine-db psql -U alchymine -d alchymine -c \
  "INSERT INTO invite_codes (code, max_uses, uses_count, is_active, note) VALUES ('DEVLOCAL', 100, 0, true, 'Local dev');" >/dev/null

echo "==> Registering dev@example.com"
curl -sf -X POST http://localhost:8200/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@example.com","password":"devpassword123","promo_code":"DEVLOCAL"}' \
  >/dev/null

echo "==> Promoting to admin"
docker exec -i alchymine-db psql -U alchymine -d alchymine -c \
  "UPDATE users SET is_admin = true WHERE email = 'dev@example.com';" >/dev/null

echo ""
echo "Done. Log in at http://localhost:3200/login"
echo "  email:    dev@example.com"
echo "  password: devpassword123"
