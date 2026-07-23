$ErrorActionPreference = "Stop"

# This script always includes compose.dev.yaml. The importer has no production
# service and refuses to run unless CUS_ENV=local is set in the container.
docker compose -f compose.yaml -f compose.dev.yaml --profile local-seed --env-file .env.example --env-file .env `
    run --rm local-seed
