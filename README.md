# Chatbolls

Canonical implementation workspace for `hub.edevs.tech`.

## Local start

```powershell
Copy-Item .env.example .env
.\scripts\start.ps1
```

По умолчанию локально запускается облачный режим. Коробочный режим запускается
тем же штатным контуром, но с явным признаком поставки:

```powershell
.\scripts\start.ps1 -Mode Cloud
.\scripts\start.ps1 -Mode SelfHosted
```

Приложение не определяет режим по домену, числу организаций или данным тарифа.
Единственный источник — `CUS_DELIVERY_MODE` со значением `CLOUD` или
`SELF_HOSTED`. В production переменная обязательна; шаблон коробочного
экземпляра `env.example` уже содержит `SELF_HOSTED`.

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

## Optional demo seed

The demo seed is a Django management command (`seed_demo`) that loads a full
fictional dataset for a Russian IIoT vendor company «Северная Верфь» (products
«Вектор» and «Репер»): organization with logo, staff with access profiles,
product catalog with offers and prices, channels and AI agents, knowledge base
with file attachments, conversations, orders, external sales, support contracts
and a public help-center portal, calls, and notifications. It is idempotent and
never runs during `start.ps1`, `docker compose up`, or migrations.

The editable data lives in
`apps/backend/hub_platform/identity/demo_seed/data/` (one JSON manifest per
domain, plus `media/` for attachments). The command is baked into the backend
image, so the same dataset works for local testing and cloud installation.

Run it only after the local dev stack is running:

```powershell
.\scripts\seed-demo.ps1
```

Or directly via management command (dry-run by default, `--apply` to write):

```
python manage.py seed_demo --apply
```

The `demo-seed` one-shot service is defined only by `compose.dev.yaml`. Outside
`DEBUG` (e.g. cloud installation) the command requires `--force`. Production
compose has no seed service.

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
