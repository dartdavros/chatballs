$ErrorActionPreference = "Stop"

docker compose run --rm backend pytest
docker compose run --rm internal-ui npm run test
docker compose run --rm internal-ui npm run typecheck
docker compose run --rm web-chat npm run typecheck
