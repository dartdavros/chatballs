$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

# Dev-контур: canonical compose.yaml + dev override (ADR-HUB-0028).
docker compose -f compose.yaml -f compose.dev.yaml --env-file .env.example --env-file .env up --build
