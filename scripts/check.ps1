$ErrorActionPreference = "Stop"

docker compose run --rm backend-app pytest
docker compose run --rm frontend npm run test
docker compose run --rm frontend npm run typecheck
docker compose run --rm web-chat npm run typecheck
