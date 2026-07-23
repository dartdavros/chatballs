# CustoCRM

Canonical implementation workspace for `hub.edevs.tech`.

## Local start

```powershell
Copy-Item .env.example .env
.\scripts\start.ps1
```

The local compose stack contains:

- isolated app, platform, and loopback-only admin Django runtimes;
- background worker;
- PostgreSQL;
- Redis;
- Internal Hub UI;
- Web Chat UI;
- local Nginx reverse proxy.

No production secrets are stored in the repository.

Default local URLs:

- App gateway: `http://app.localhost/`
- Platform health: `http://platform.localhost/api/v1/health/live/`
- Django admin (loopback only): `http://127.0.0.1:18001/admin/`
- Internal Hub UI (direct Vite): `http://localhost:5173`
- Web Chat: `http://localhost:5175`
- App API (direct): `http://localhost:8010/api/v1`

Local accounts (TOTP disabled). These credentials are fixed — do not change them:

- OWNER — `owner@edevs.tech` / `Owner-Local-2026`
- OPERATOR — `a.kotova@edevs.tech` / `Operator-Local-2026`

Bootstrap the organization and both accounts:

```powershell
docker compose run --rm backend-app python manage.py bootstrap_owner --email owner@edevs.tech --password Owner-Local-2026 --name "Иван Петров"
```

## Optional local demo seed

The local demo seed is explicit and idempotent: it creates the documented local
accounts and a connected set of departments, products, channels, integrations,
AI agents, conversations, orders, and command-center data. It never runs during
`start.ps1`, `docker compose up`, or migrations.

Run it only after the local dev stack is running:

```powershell
.\scripts\seed-local.ps1
```

The data manifest and importer live in `dev/local-seed/`. The explicit
`local-seed` one-shot service is defined only by `compose.dev.yaml`, runs with
the local migration DB role, is excluded from the backend image, and the
importer refuses any environment other than `CUS_ENV=local`. Production compose
has no seed service or seed command.

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
docker compose run --rm backend-app pytest

# Frontend unit tests (vitest)
docker compose run --rm frontend npm run test

# End-to-end (Playwright, internal-ui) — auto-starts the dev server
npx playwright install chromium   # one-time
npx playwright test --project=internal-ui
```

Backend pytest configuration lives in `apps/backend/pytest.ini` (it must sit
next to `manage.py` so it is also visible inside the backend container).
