# Chatballs

Canonical implementation workspace for Chatballs.

## Быстрый старт (одна минута)

Нужен только Docker (Docker Desktop на Windows/macOS или Docker Engine с Compose
на Linux). Никаких параметров заранее задавать не нужно — всё спросит браузер.

Windows (PowerShell):

```powershell
git clone <URL репозитория> chatballs
cd chatballs/code/chatballs
.\scripts\start.ps1
```

Linux / macOS:

```bash
git clone <URL репозитория> chatballs
cd chatballs/code/chatballs
./scripts/start.sh
```

Скрипт копирует `.env.example` в `.env` (если его нет), собирает образы и
поднимает стек. Когда в логах появится готовность, откройте
**http://localhost** — вместо входа система покажет **мастер первого запуска**:
название организации, ваше имя, e-mail и пароль владельца, переключатель
«Установить демо-данные». После кнопки «Начать» вы сразу в приложении под
владельцем. Мастер доступен только пока в системе нет ни одной организации;
после создания владельца он закрывается навсегда.

### Демо-данные

Демо — вымышленное ателье «Норд» (дизайн-базлайн v2): сотрудники и группы,
агенты с подключениями Telegram/MAX/почта/веб-виджет, база знаний с
вложениями, диалоги во всех состояниях (AI ведёт, ждёт оператора, ведёт
сотрудник, закрыт, спам, архив), метки, приоритеты, заметки, шаблоны
ответов, голосовые (живая речь из открытого датасета Mozilla Common Voice, CC0),
портал поддержки со статьями, звонки, уведомления и история использования AI за
30 дней. Видимая часть повторяет кадры дизайн-базлайна v2 один в один. Набор покрывает каждую модель системы —
это проверяет тест `identity.test_seed_demo`.

Демо ставится в вашу организацию и удаляется целиком одной кнопкой: **Настройки →
Демо-данные**. Там же — учётные записи демо-сотрудников из разных групп, чтобы
посмотреть систему их глазами (пароль общий и намеренно публичный —
`Chatballs-Demo-2026`). Ваши данные при удалении не затрагиваются: сид ведёт
реестр созданных записей и удаляет ровно их.

Для разработки то же доступно из командной строки:

```bash
docker compose run --rm backend-app python manage.py seed_demo --organization <slug> --apply
docker compose run --rm backend-app python manage.py seed_demo --organization <slug> --remove
```

Редактируемые данные — `apps/backend/chatballs/identity/demo_seed/data/`
(JSON-манифест на домен, `media/` — вложения, аватары, голосовые). Голосовые
сообщения читаются из `media/voice/` (см. README там); если файла нет, сообщение
пропускается.

### Обновление установки со старым именем (Chatballs / hub → Chatballs)

Установки, развёрнутые до переименования (compose-проект `chatballs`, база
`chatballs`, роли Postgres `chatballs_*`, переменные `CHATBALLS_*`/`CHATBALLS_*`),
переводятся на новые имена одним скриптом — данные остаются на месте:

```bash
# prod: сначала переместите каталог релизов и инстанса
mv /opt/chatballs /opt/chatballs
CHATBALLS_INSTANCE_DIR=/opt/chatballs/instance ./deploy/migrate/rename-to-chatballs.sh
./chatballs deploy
```

```bash
# dev-стек из каталога репозитория
CHATBALLS_INSTANCE_DIR="$PWD" CHATBALLS_COMPOSE_ARGS="-f compose.dev.yaml --env-file .env.example"   deploy/migrate/rename-to-chatballs.sh
docker compose -f compose.yaml -f compose.dev.yaml --env-file .env.example --env-file .env up -d
```

Скрипт останавливает старый compose-проект, переписывает `.env` (резервная
копия рядом, `.env.bak-custocrm`), переименовывает роли, схему RLS (и её GUC),
базу и печатает итог. Cookie сессий меняют имя — пользователи входят заново.
В CI/CD корень деплоя теперь `/opt/chatballs`.

### Режим поставки

По умолчанию локально запускается облачный режим. Коробочный режим — тем же
контуром с явным признаком поставки:

```powershell
.\scripts\start.ps1 -Mode Cloud
.\scripts\start.ps1 -Mode SelfHosted
```

Приложение не определяет режим по домену, числу организаций или данным.
Единственный источник — `CHATBALLS_DELIVERY_MODE` со значением `CLOUD` или
`SELF_HOSTED`. В production переменная обязательна; шаблон коробочного
экземпляра `env.example` уже содержит `SELF_HOSTED`.

### Что поднимается

- изолированные Django-рантаймы app, platform и loopback-only admin;
- фоновый worker (outbox, поллинг мессенджеров, установка демо);
- PostgreSQL и Redis;
- Internal Hub UI и Web Chat UI;
- локальный Nginx reverse proxy.

Секретов production в репозитории нет.

Локальные адреса:

- Приложение: `http://localhost` (то же — `http://app.localhost/`)
- Health платформы: `http://platform.localhost/api/v1/health/live/`
- Django admin (только loopback): `http://127.0.0.1:18001/admin/`
- Internal Hub UI напрямую (Vite): `http://localhost:5173`
- Web Chat: `http://localhost:5175`
- App API напрямую: `http://localhost:8010/api/v1`

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
