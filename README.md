# Chatballs

Canonical implementation workspace for Chatballs.

## Быстрый старт (одна минута)

Нужен только Docker (Docker Desktop на Windows/macOS или Docker Engine с Compose
на Linux). Ни одной переменной задавать не нужно и негде: у продукта нет `.env`.
Организацию, владельца, домены, интеграции, почту и хранилище человек настраивает
в интерфейсе.

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

Настраивать нечего: файла `.env` у продукта нет, секреты инстанса (ключ
подписи, пароли ролей БД) генерирует сам первый старт и держит их в томе
`chatballs-secrets`.

Если положить рядом со скриптом `release.env` со страницы релиза, образы
скачаются из реестра по digest и сборки не будет — это самый быстрый путь.
Без `release.env` стек собирается из исходников: так работают те, кто правит
код. Когда в логах появится готовность, откройте
**http://localhost** — вместо входа система покажет **мастер первого запуска**:
название организации, ваше имя, e-mail и пароль владельца, переключатель
«Установить демо-данные». После кнопки «Начать» вы сразу в приложении под
владельцем. Мастер доступен только пока в системе нет ни одной организации;
после создания владельца он закрывается навсегда.

### Доступ по http и переход на TLS

Свежая установка отвечает по обычному http — по адресу сервера, пока домена и
сертификата ещё нет. Продукт не уводит себя на https принудительно: этим
занимается шлюз, когда у него появляется настоящий домен и сертификат.
Жёсткость транспорта включается сама по факту TLS: запрос пришёл по https —
cookie получают префикс `__Host-`, флаг `Secure` и HSTS; по http — обычные
имена без `Secure`. Настраивать для этого нечего.

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

### Режим поставки

По умолчанию локально запускается облачный режим. Коробочный режим — тем же
контуром с явным признаком поставки:

```powershell
.\scripts\start.ps1 -Mode Cloud
.\scripts\start.ps1 -Mode SelfHosted
```

Приложение не определяет режим по домену, числу организаций или данным.
Коробка по умолчанию считает себя `SELF_HOSTED`; облачный контур выставляет
`CHATBALLS_DELIVERY_MODE=CLOUD` явно. Задавать что-либо при установке не
нужно и негде — файла с переменными у продукта нет.

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
