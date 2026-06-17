$ErrorActionPreference = "Stop"

docker compose run --rm backend python manage.py test
docker compose run --rm internal-ui npm run typecheck
docker compose run --rm checkout npm run typecheck
docker compose run --rm web-chat npm run typecheck
