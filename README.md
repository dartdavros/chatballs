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
- Checkout UI;
- Web Chat UI;
- local Nginx reverse proxy.

No production secrets are stored in the repository.

Default local URLs:

- Internal Hub UI: `http://localhost:5173`
- Django admin: `http://localhost:8010/admin/`
- Checkout: `http://localhost:5174`
- Web Chat: `http://localhost:5175`
- Backend API: `http://localhost:8010/api/v1`

Create or refresh the local OWNER account:

```powershell
docker compose run --rm backend python manage.py bootstrap_owner --email owner@edevs.tech --password local-owner-password --name "Edevs Owner"
```
