$ErrorActionPreference = "Stop"

# Portal-only demo data: no users, passwords, roles, sessions, or credentials.
docker compose -f compose.yaml -f compose.dev.yaml --profile support-portal-seed `
    --env-file .env.example --env-file .env run --rm support-portal-seed
