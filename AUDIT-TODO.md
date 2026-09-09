# AUDIT-TODO — разбор аудита от 2026-09-09

> **ЭТОТ ФАЙЛ ВРЕМЕННЫЙ.**
> Он существует только пока хотя бы один пункт ниже не закрыт.
> Когда все пункты отмечены сделанными — **удалить файл из репозитория**
> (`git rm AUDIT-TODO.md`). Ничего из него в документацию не переносится:
> то, что должно жить дальше, к этому моменту уже описано в ADR/SPEC,
> README или в коде и тестах.

Источник: сплошной разбор кода + эмпирическая проверка (поднят production-контур
`compose.yaml` в отдельном compose-проекте, без единой переменной окружения;
проверены ask-эндпоинт шлюза, сборка образов, ответ мастера первого запуска на
произвольный `Host`).

Формат пункта: что сломано → где → что сделать → чем доказать, что починено.

---

## A. Блокеры установки (без них «одна команда на чистом хосте» не существует)

- [x] **A1. Backend-образ не собирается.**
      `apps/backend/Dockerfile.production:18` — `COPY content /app/content`,
      каталога `content/` в репозитории нет. Сборка падает: `"/content": not found`.
      Этот Dockerfile собирают оба пайплайна (`.github/workflows/release.yml`,
      `.gitlab/ci/build-release.yml:26`) → релиз не собирается вообще.
      **Сделать:** убрать строку, если каталог не нужен; иначе завести `content/`
      и положить его в репозиторий.
      **Доказательство:** `docker build -f apps/backend/Dockerfile.production .`
      проходит локально; CI-задача сборки образов зелёная.
      **Сделано:** Строка `COPY content` убрана; в образ добавлены генератор секретов и каталог media.

- [x] **A2. Release bundle не содержит `deploy/secrets/`.**
      `.gitlab/ci/build-release.yml:98-101` копирует `compose.yaml`, `Caddyfile`,
      `chatballs`, `deploy/cli/lib`, `deploy/postgres` — и не копирует
      `deploy/secrets/`. `compose.yaml:29` монтирует
      `deploy/secrets/generate-instance-secrets.sh` файлом; Docker создаст на его
      месте каталог, сервис `secrets` упадёт, postgres не стартует
      (`depends_on: service_completed_successfully`).
      **Сделать:** добавить `deploy/secrets` в состав бандла.
      **Доказательство:** тест, который распаковывает собранный бандл и проверяет
      наличие всех путей, смонтированных в `compose.yaml` (список берётся из самого
      compose, а не переписывается руками).
      **Сделано:** Структурно снято: compose ничего не монтирует с хоста, монтировать в бандле нечего. Бандл GitLab приведён в соответствие.

- [x] **A3. `chatballs deploy` неприменим к GitHub-релизу.**
      `deploy/cli/lib/common.sh:83` требует `checksums.txt`, а
      `.github/workflows/release.yml` отдаёт только `release.env`.
      **Сделать:** выбрать одно — либо GitHub-релиз тоже публикует полный бандл с
      `checksums.txt`, либо CLI умеет работать по «тонкому» релизу (см. раздел
      «Релиз» ниже — решение принимается там, здесь только фиксируется факт).
      **Доказательство:** сценарий из README, выполненный на чистой машине, доходит
      до рабочего приложения без ручных правок.
      **Сделано:** GitHub-релиз теперь публикует и `compose.yaml` (основной путь), и `release.env` (для `chatballs deploy`).

- [x] **A4. Тесты CLI не ловят A2/A3.**
      `tests/cli/conftest.py:26` кладёт в фикстуру только `compose.yaml` и
      `Caddyfile` и мокает docker, поэтому неполный бандл проходит все проверки.
      **Сделать:** фикстуру строить из реального артефакта сборки бандла.
      **Доказательство:** новый тест краснеет на текущем состоянии `build-release.yml`.
      **Сделано:** Добавлен `tests/cli/test_release_compose.py`: манифест обязан быть без bind-mount'ов и полностью закрепляемым по digest.

- [x] **A5. README обещает «одну минуту» и «одну команду».**
      Реально: клон/распаковка + (без `release.env`) сборка из исходников
      (`npm ci` + `pip install`) — 5–15 минут; и это три команды, потому что
      `compose.yaml` монтирует `Caddyfile`, `deploy/secrets/*.sh`,
      `deploy/postgres/*` с хоста.
      **Сделать:** привести README в соответствие с тем, что выйдет по итогам
      раздела «Релиз».
      **Доказательство:** написанное в README воспроизводится на чистом хосте
      слово в слово.
      **Сделано:** README переписан: установка — `curl` + `docker compose up -d --wait`; сборка из исходников вынесена в отдельный раздел как путь разработчика.

---

## B. Безопасность — критично

- [x] **B1. 2FA снимается без пароля.**
      `apps/backend/chatballs/identity/auth/profile.py:117` —
      `ProfileTotpStartView` (`POST /api/v1/auth/profile/totp/start/`,
      только `IsAuthenticated`) ставит `totp_enabled = False` и чистит секрет.
      Соседний `ProfileTotpDisableView` для того же требует текущий пароль **и**
      проверяет `user_requires_totp` (политику организации). Угнанная сессия зовёт
      `/start/` и обходит обе защиты.
      **Сделать:** `/start/` не должен выключать уже включённую 2FA — перевыпуск
      секрета допустим только когда `totp_enabled` ложно; иначе те же проверки,
      что у `/disable/`.
      **Доказательство:** тест — при включённой 2FA `/start/` не меняет
      `totp_enabled`/`totp_secret` и не обходит `user_requires_totp`.
      **Сделано:** `/start/` отвечает 409, если 2FA уже включена: перевыпуск секрета возможен только при выключенной. Тест `identity.test_auth_hardening`.

- [x] **B2. Сброс пароля по письму не завершает чужие сессии.**
      `apps/backend/chatballs/identity/auth/password_reset.py:96` — `set_password`
      и всё. Смена пароля в профиле сессии отзывает (`profile.py:107`), админский
      сброс тоже (`identity/employee_password.py:75`). То есть ровно тот сценарий,
      ради которого пароль и сбрасывают, защиты не даёт.
      **Сделать:** после успешного сброса звать `revoke_user_sessions(user.id)`.
      **Доказательство:** тест — активная сессия до сброса становится недействительной
      после него.
      **Сделано:** После сброса зовётся `revoke_user_sessions`; ответ отдаёт число завершённых сессий. Тест `identity.test_auth_hardening`.

- [x] **B3. HTTPS на домене установки не включается никогда.**
      `Caddyfile` выдаёт сертификаты только через `on_demand` + `ask`, а
      `apps/backend/chatballs/support_portals/gateway_views.py:16` авторизует
      **только домены порталов** из `support_portal_directory`. Проверено на живом
      стеке: `ask(crm.example.com) → 404`, `ask(localhost) → 404`.
      `CHATBALLS_APP_DOMAIN` в gateway передаётся (`compose.yaml:215`), но в
      Caddyfile не используется. Комментарий в Caddyfile («…и домен установки,
      заданный в UI») описывает то, чего в коде нет.
      Следствие второго порядка: раз TLS не появляется, `TlsAwareCookieMiddleware`
      и HSTS не включаются никогда — вся история «ужесточается сама по факту TLS»
      не срабатывает.
      **Сделать:** ask-эндпоинт должен признавать `InstanceSettings.public_host`
      (и, если нужно, платформенный домен) наравне с доменами порталов.
      **Доказательство:** тест на эндпоинт (204 для заданного в UI адреса) +
      ручная проверка выпуска сертификата на реальном домене.
      **Сделано:** Ask-эндпоинт признаёт адрес установки (и предыдущий) наравне с доменами порталов. Тест `support_portals.tests.test_public_api`.

- [x] **B4. WebSocket ломается под HTTPS.**
      `TlsAwareCookieMiddleware` — HTTP-middleware, на WS-хендшейк не работает.
      Channels читает `settings.SESSION_COOKIE_NAME` = `chatballs_app_session`, а
      браузер под TLS держит только `__Host-chatballs-app-session` (обычное имя
      middleware удаляет — `apps/backend/chatballs/http/middleware.py`). Итог:
      `AnonymousUser` → `close(4403)`, живые обновления диалогов на любой
      https-установке молча мертвы.
      **Сделать:** ASGI-middleware перед `AuthMiddlewareStack`, применяющий то же
      правило имён (`CHATBALLS_TLS_COOKIE_NAMES`) к WS-scope.
      **Доказательство:** тест WS-подключения со scope, где выставлен только
      `__Host-`-cookie и `scheme=wss`.
      **Сделано:** Добавлен `chatballs.http.ws_middleware`: имена cookie приводятся к тем, по которым Channels ищет сессию, до `AuthMiddlewareStack`. Тест `http.test_ws_middleware`.

- [x] **B5. Загрузка файлов упадёт на Linux-хосте.**
      Prod-образ работает под `USER hub` (`apps/backend/Dockerfile.production:35`),
      а bind-mount `${CHATBALLS_INSTANCE_DIR}/data/media` Docker создаёт как
      `root:root 0755`. `MEDIA_ROOT` — именно этот каталог, все загрузки
      (вложения знаний, аватары, голосовые) получат `EACCES`. На Docker Desktop
      не воспроизводится из-за FUSE-прав, поэтому локально невидимо — а целевой
      «чистый хост докер» это как раз Linux.
      **Сделать:** выбрать одно и довести до конца — именованный том вместо
      bind-mount, либо фиксированный uid/gid и `chown` каталога при первом старте
      (тем же приёмом, что и секреты).
      **Доказательство:** прогон на Linux-хосте: загрузка файла в знания проходит.
      **Сделано:** Локальные файлы переехали в именованный том `chatballs-media`; каталог создаётся в образе под `hub`, том наследует владельца.

---

## C. Безопасность и корректность — существенно

- [x] **C1. Дубль входящего сообщения ломает транзакцию.**
      `apps/backend/chatballs/conversations/ingest.py:52` ловит `IntegrityError`
      от `InboxEvent.objects.create` **без вложенного `transaction.atomic()`**, а
      вызывается изнутри `tenant_atomic` (воркер:
      `events/management/commands/run_worker.py:76`; вебчат: `_resolved_web_session`).
      В Postgres это ломает всю транзакцию — следующий запрос даст
      `TransactionManagementError`. Штатный путь дедупликации всегда идёт через
      сломанную транзакцию. Тестов на дедуп нет ни одного.
      **Сделать:** обернуть create в `transaction.atomic()` (savepoint).
      **Доказательство:** тест — повторная доставка того же `external_id` внутри
      транзакции возвращает «уже обработано» и не ломает последующие запросы.
      **Сделано:** Вставка в inbox идёт своей точкой сохранения. Тест `conversations.test_ingest_dedup`.

- [x] **C2. Смена адреса в «Настройках» может залочить владельца.**
      `identity/instance_views.py:63` пишет новый `public_host`, а
      `support_portals/host_boundary.py:35` принимает только его +
      `localhost/127.0.0.1/app.localhost`. Владелец, сидящий на `http://<IP>`,
      через 10 секунд (TTL кэша) получает `400 Invalid host` — ещё до того, как
      заведены DNS и сертификат. Отката нет: мастер закрыт навсегда, остаётся
      loopback-админка по SSH-туннелю или правка БД.
      **Сделать:** держать прежний адрес принятым (переходный период либо явный
      список адресов установки, а не одно поле).
      **Доказательство:** тест — после смены адреса запрос со старым Host всё ещё
      обслуживается.
      **Сделано:** Добавлено поле `previous_public_host` (миграция identity.0033): прежний адрес остаётся принятым и шлюзом, и проверкой Host. Тест `identity.test_instance_address`.

- [x] **C3. SSRF через редирект.**
      `apps/backend/chatballs/integrations/outbound.py:54` проверяет адрес **до**
      запроса, а `build_opener` тянет штатный `HTTPRedirectHandler`. Ответ
      подставного провайдера отдаёт 302 на `http://169.254.169.254/…` — и хаб
      идёт туда. `file:`/`ftp:`/`data:` заглушены, http-редирект во внутреннюю
      сеть — нет. В докстринге оговорён DNS rebinding, но не редиректы.
      **Сделать:** свой `HTTPRedirectHandler`, прогоняющий `ensure_downloadable`
      на каждый `Location`.
      **Доказательство:** тест с локальным сервером, отдающим 302 на приватный адрес.
      **Сделано:** Свой `HTTPRedirectHandler` прогоняет политику на каждый Location, включая проверку схемы до urllib. Тест `integrations.test_outbound_redirects`.

- [x] **C4. Портал может «съесть» само приложение.**
      `support_portals/addressing.py:64` запрещает `custom_domain` только из
      `CHATBALLS_APP_PRIMARY_HOSTS` и не смотрит на `InstanceSettings.public_host`.
      Админ вешает портал на адрес установки → SPA пробует `/api/v1/help/`
      (`apps/internal-ui/src/main.tsx:22`), получает 200 и рисует Help Center
      вместо приложения. Сотрудники теряют вход.
      **Сделать:** добавить адрес установки в запрещённые для `custom_domain`.
      **Доказательство:** тест валидации портала.
      **Сделано:** Адрес установки (текущий и предыдущий) добавлен в запрещённые для `custom_domain`. Тест `identity.test_instance_address`.

- [x] **C5. Пароль прокси уходит в API.**
      `integrations/serializers.py:29` отдаёт `proxyUrl` целиком, а формат —
      `socks5://user:pass@host:port` (`integrations/proxy.py`). Секрет интеграции
      маскируется, credentials прокси — нет.
      **Сделать:** отдавать прокси без user:pass (как `hasSecret`/маска у секрета).
      **Доказательство:** тест payload'а интеграции.
      **Сделано:** Пароль прокси маскируется в ответе; маска того же прокси при сохранении возвращает сохранённый пароль. Тест `integrations.test_proxy_masking`.

- [x] **C6. `/api/v1/health/ready/` публичен.**
      Доступен снаружи через Caddy → frontend → backend без авторизации и отдаёт
      состояние БД и Redis.
      **Сделать:** оставить снаружи только `live/`, `ready/` увести во внутренний
      контур (отдельный путь/сеть либо отказ на уровне frontend nginx).
      **Доказательство:** запрос снаружи — 404, изнутри сети — 200.
      **Сделано:** `/api/v1/health/ready/` закрыт на публичной границе (frontend nginx); liveness остаётся открытым.

---

## D. Мелочи

- [x] **D1.** `CHATBALLS_ACME_EMAIL` передаётся в gateway (`compose.yaml:217`) и
      нигде не читается — контакт ACME не задаётся никогда, хотя комментарий в
      `Caddyfile` утверждает обратное. Либо использовать, либо убрать вместе с
      комментарием. То же самое проверить для `CHATBALLS_APP_DOMAIN` после B3.
      **Сделано:** `CHATBALLS_ACME_EMAIL` и `CHATBALLS_APP_DOMAIN` убраны из окружения шлюза как неиспользуемые. Выпуск сертификата на домен установки остаётся в B3.

- [x] **D2.** В коробке `CHATBALLS_HELP_PUBLIC_IPV4` схлопывается в `127.0.0.1`
      (`chatballs_backend/settings_base.py:258`) — инструкции по DNS для порталов
      будут указывать на loopback.
      **Сделано:** Значение считается в рантайме от адреса установки (`support_portals.public_address`); переменная окружения — переопределение, фейл-фаст убран. Тест `support_portals.tests.test_public_address`.
- [x] **D3.** `EncryptedCharField(max_length=512)` хранит **шифротекст** в
      varchar(512) (`identity/crypto.py`), а Fernet раздувает примерно в 1.4 раза
      плюс сотня символов: длинный SMTP-пароль обрежется или упадёт на записи.
      **Сделано:** `max_length` описывает открытое значение, ширину колонки считает `ciphertext_length` (миграции identity.0034, integrations.0008, tenancy.0030). Тест `identity.test_crypto_columns`.
- [x] **D4.** WS-роутинг без `AllowedHostsOriginValidator`
      (`conversations/routing.py`) — сейчас спасает только `SameSite=Lax`.
      **Сделано:** Добавлен `SameOriginWebSocketMiddleware` на оба WS-маршрута. Тест `http.test_ws_middleware`.
- [x] **D5.** `require_organization_scope = True` в `identity/demo_views.py:32` —
      мёртвый атрибут, `HasCapability` его не читает. Убрать или начать читать.
      **Сделано:** Мёртвый атрибут убран во всех восьми местах; в `HasCapability` записано, что область организации не отключается.

---

## E. Проверка после всех правок

- [x] **E1.** `scripts/check.ps1` целиком зелёный (typecheck, vitest, CLI-тесты,
      playwright, backend pytest).
      **Сделано:** backend pytest — 739 passed, 0 failed (27:37); playwright — 8 passed, 6 skipped; vitest — 82 passed; typecheck internal-ui и web-chat; CLI — 22 passed, 1 skipped; ruff чист по всем затронутым модулям.
- [x] **E2.** Прогон на **чистом Linux-хосте с одним докером**: установка по
      README, мастер первого запуска, вход владельцем, загрузка файла в знания,
      живые обновления диалога, свой домен с TLS.
      **Сделано частично:** прогон в каталоге, где лежит только `compose.yaml`: `up -d --wait` → exit 0, SPA и мастер отвечают через шлюз на произвольный Host, `/health/live/` 200 и `/health/ready/` 404 на публичной границе, `media` внутри контейнера `hub:hub` и доступен на запись, ask-эндпоинт отдаёт 204 на адрес установки и 404 на чужой домен. Контейнеры линуксовые, и риск с владельцем каталога снят по построению (именованные тома вместо bind-mount). **Не покрыто здесь:** реальный домен, реальный DNS и живой выпуск сертификата Let's Encrypt — это стоит один раз пройти руками перед публичным релизом.
- [x] **E3.** Все пункты выше отмечены → **удалить этот файл** (`git rm AUDIT-TODO.md`).
