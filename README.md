# Edevs Hub

Canonical implementation workspace for `hub.edevs.tech`.

## Local start

```powershell
Copy-Item .env.example .env
.\scripts\start.ps1
```

The local compose stack contains:

- Django ASGI backend and background worker;
- PostgreSQL;
- Redis;
- Internal Hub UI;
- Web Chat UI;
- local Nginx reverse proxy.

No production secrets are stored in the repository.

Default local URLs:

- Internal Hub UI: `http://localhost:5173`
- Django admin: `http://localhost:8010/admin/`
- Web Chat: `http://localhost:5175`
- Backend API: `http://localhost:8010/api/v1`

Local accounts (TOTP disabled). These credentials are fixed — do not change them:

- OWNER — `owner@edevs.tech` / `Owner-Local-2026`
- OPERATOR — `a.kotova@edevs.tech` / `Operator-Local-2026`

Bootstrap the organization and both accounts:

```powershell
docker compose run --rm backend python manage.py bootstrap_owner --email owner@edevs.tech --password Owner-Local-2026 --name "Иван Петров"
```

## Tests

All suites run in Docker, so no manual environment is required — the test
runners auto-detect themselves and relax production hardening (secret-key
fail-fast, SSL redirect, throttling) for the duration of the run.

Run everything (backend tests, frontend unit tests, typechecks):

```powershell
.\scripts\check.ps1
```

Individual suites:

```powershell
# Backend (pytest + pytest-django)
docker compose run --rm backend pytest

# Frontend unit tests (vitest)
docker compose run --rm internal-ui npm run test

# End-to-end (Playwright, internal-ui) — auto-starts the dev server
npx playwright install chromium   # one-time
npx playwright test --project=internal-ui
```

Backend pytest configuration lives in `apps/backend/pytest.ini` (it must sit
next to `manage.py` so it is also visible inside the backend container).
