# Alchymine docker compose wrapper
#
# Reads secrets from .secrets/.env instead of the repo root .env.
# The secrets directory is gitignored and kept out of the repo root so
# AI coding tools (e.g. Claude / Codex via Archon) that spawn subprocesses
# in this repo cannot auto-load them via Bun's .env auto-loading.
#
# Usage:
#   ./run.ps1 up -d
#   ./run.ps1 logs -f api
#   ./run.ps1 down
#   ./run.ps1 config    # to verify env substitution

docker compose --env-file .secrets/.env -f infrastructure/docker-compose.yml @args
