# Chatballs

Canonical implementation workspace for Chatballs.

## Установка (одна команда)

Нужен только Docker с плагином Compose. Ни одной переменной задавать не нужно и
негде: у продукта нет `.env`. Организацию, владельца, домены, интеграции, почту и
хранилище человек настраивает в интерфейсе.

Весь дистрибутив — один файл `compose.yaml` со страницы релиза: ссылки на образы
в нём закреплены по digest, а Caddyfile, init-скрипты базы и генератор секретов
лежат внутри образов. Рядом с файлом ничего лежать не должно.

Linux / macOS:

```bash
curl -fsSL https://github.com/dartdavros/chatballs/releases/latest/download/compose.yaml -o compose.yaml
docker compose up -d --wait
```

Windows (PowerShell):

```powershell
curl.exe -fsSL https://github.com/dartdavros/chatballs/releases/latest/download/compose.yaml -o compose.yaml
docker compose up -d --wait
```

`--wait` держит команду до готовности стека: когда она вернула управление,
установка отвечает. Откройте **http://localhost** (или адрес сервера) — вместо
входа система покажет **мастер первого запуска**: название организации, ваше имя,
e-mail и пароль владельца, переключатель «Установить демо-данные». После кнопки
«Начать» вы сразу в приложении под владельцем. Мастер доступен только пока в
системе нет ни одной организации; после создания владельца он закрывается
навсегда.

Секреты инстанса (ключ подписи, пароли ролей БД) генерирует сам первый старт и
держит в томе `chatballs-secrets`. Состояние установки живёт в именованных томах
`chatballs-*` — установка не зависит от того, из какого каталога её запустили.

Обновление — тот же файл новой версии и та же команда:

```bash
curl -fsSL https://github.com/dartdavros/chatballs/releases/latest/download/compose.yaml -o compose.yaml
docker compose up -d --wait
```

Миграции прогоняет one-shot сервис `init` на каждом старте. Откат — прежняя
копия `compose.yaml` и снова та же команда.

### Запуск из исходников (разработка)

Тем, кто правит код, релизный файл не нужен: стек собирается локально.

```powershell
git clone <URL репозитория> chatballs
cd chatballs
.\scripts\start.ps1
```

```bash
git clone <URL репозитория> chatballs
cd chatballs
./scripts/start.sh
```

Первая сборка занимает минуты (`npm ci` + `pip install`). Dev-контур держит
состояние в `./data`, публикует порты Postgres/Redis и подменяет frontend на
Vite с HMR — см. `compose.dev.yaml`.

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

По умолчанию коробка считает себя `SELF_HOSTED`; облачный контур выставляет
`CHATBALLS_DELIVERY_MODE=CLOUD` явно. Приложение не определяет режим по домену,
числу организаций или данным. Задавать что-либо при установке не нужно и негде.

Локально `scripts/start.ps1` поднимает облачный режим; коробочный — тем же
контуром с явным признаком поставки:

```powershell
.\scripts\start.ps1 -Mode Cloud
.\scripts\start.ps1 -Mode SelfHosted
```

### Что поднимается

- изолированные Django-рантаймы app, platform и loopback-only admin;
- фоновый worker (outbox, поллинг мессенджеров, установка демо);
- PostgreSQL и Redis;
- Internal Hub UI и Web Chat UI одним nginx-образом;
- шлюз Caddy — единственная публичная граница (80/443).

Секретов production в репозитории нет.

Локальные адреса dev-контура:

- Приложение: `http://localhost` (то же — `http://app.localhost/`)
- Health платформы: `http://platform.localhost/api/v1/health/live/`
- Django admin (только loopback): `http://127.0.0.1:18001/admin/`
- Internal Hub UI напрямую (Vite): `http://localhost:5173`
- Web Chat: `http://localhost:5175`
- App API напрямую: `http://localhost:8010/api/v1`

### Доступ по http и переход на TLS

Свежая установка отвечает по обычному http — по адресу сервера, пока домена и
сертификата ещё нет. Продукт не уводит себя на https принудительно.

Когда у установки появляется домен, владелец вписывает его в **Настройки →
Адрес установки**. С этого момента шлюз выписывает на него сертификат сам, при
первом же запросе по https: он спрашивает разрешение у самой установки, и она
подтверждает свой адрес и адреса опубликованных порталов помощи. Прежний адрес
остаётся принятым, чтобы смена не выбросила того, кто её делает.

Жёсткость транспорта включается сама по факту TLS: запрос пришёл по https —
cookie получают префикс `__Host-`, флаг `Secure` и HSTS; по http — обычные
имена без `Secure`. Настраивать для этого нечего.

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
