# T-190: файлы, шаблоны и составные ответы

Проверки 16.11.2026 в основной рабочей копии. Принятый вход T-189:
`ad8dbe15248c8ab970fd5a3a85142a4b18e41478`.

## Реализованный объём

- Scoped multipart/upload и streaming/download используют tenant storage,
  реальные UUID файлов, SHA256 фактических байтов, штатные имена, запреты типов,
  квоты и лимит 20 MiB с более узкими ограничениями канала. Исходное аудио,
  включая замаскированные сигнатуры и voice-вложения, URL/base64 не принимаются.
- Durable uploadId резервирует приватный ключ до записи. Полный новый файл
  получает 201; совпадающий повтор — 200 с теми же fileId/expiresAt; конфликт —
  409. Ошибка/обрыв не публикует файл или Message, резерв и частичные байты
  убираются; повтор восстанавливает незавершённую попытку.
- GET требует текущего authorizationId и реально выданного этому разрешению
  grant из trigger/страницы истории либо своей завершённой загрузки. Известный
  ID будущего/чужого файла доступа не даёт. Полный ответ 200, безопасный
  Content-Disposition, no-store/nosniff; Range не обязателен. ASGI передаёт
  асинхронные блоки по 64 KiB, повторяя допуск перед каждым блоком.
- Staging 24 часа; повтор не продлевает срок. Cleanup учитывает активные requests,
  delivery и опубликованные Message. Native удаление диалога сразу освобождает
  staging и квоту. Отзыв возможности, смена политики, удаление исходного
  сообщения и истечение срока закрывают чтение.
- Каталог выдаёт только явно выбранные id/revision/purpose/native dataSchema/
  representations. PostgreSQL generation монотонна при edit/A→B→A/delete/recreate.
  Инструкции навыков, знания, примеры, HTML/CSS и srcDoc не экспортируются.
- Formatted проверяет схему/данные/id/revision и использует штатный render_template,
  sanitization и sandbox snapshot. WEB получает native presentation, остальные
  каналы — native text. Готовый snapshot защищён от изменения на уровне БД;
  история выдаёт текст без srcDoc. Неизвестная/сменившаяся версия даёт 409.
- Contact_request использует штатный Message/transport и словарь на языке
  организации, включая native WEB-команду; сотрудником диалог не захватывается.
- Весь упорядоченный batch с уникальными itemId проверяется до первого Message.
  Каждый item имеет собственные Message и квитанцию, готовые элементы не
  повторяются. Текущие полномочия, контент, версии, сроки и канал проверяются
  при сохранении и передаче. FIFO сохраняется при partial/unknown; перехват
  подавляет остаток без повторного запуска бизнес-логики агента.

Продуктовые UI-компоненты и layout не менялись; используется существующий renderer
SPEC-0035. Инициативные сообщения и UI настройки внешнего исполнения остаются
объёмом последующих задач. Широкий component-external-agent не заявляется готовым.

## Штатное окружение и сборки

По отдельному разрешению владельца собраны и пересозданы только backend-app и
backend-admin. PostgreSQL, Redis, volumes, аккаунты и настройки не пересоздавались.
Применены additive migrations ai.0036, tenancy.0086 и tenancy.0087.
После обновления readiness на backend:8010 и через frontend:5174 вернул
`status=ok, database=true, redis=true`.

```powershell
docker compose -f compose.yaml -f compose.dev.yaml build backend-app
docker compose -f compose.yaml -f compose.dev.yaml up -d --no-deps --no-build backend-app backend-admin
docker compose -f compose.yaml -f compose.dev.yaml exec -T backend-admin python manage.py check
docker compose -f compose.yaml -f compose.dev.yaml exec -T backend-admin python manage.py makemigrations --check --dry-run
docker compose -f compose.yaml exec -T frontend npm --prefix /app run build
```

Backend build успешна, image:
`sha256:7e7f1fc308e630fbcd96c74c0e7dbe86cfb76974c82260d4c049956e9306a6e2`.
Internal-ui: TypeScript и Vite успешны (4606 modules). Исходники frontend не
менялись; сборка отдельного web-chat здесь не заявляется. Check: 0 issues;
makemigrations: No changes detected.

Первоначальный backend-контейнер не содержал canonicalization.yaml: после
разрешённого обновления контрактный smoke прошёл. Первоначальная host-сборка
frontend обнаружила отсутствующие workspace links; штатная сборка выполнена
в существующем frontend-контейнере без изменения зависимостей. Первый сбор
новых тестов обнаружил отсутствие Pillow: тест PNG использует stdlib struct/zlib,
дополнительных зависимостей не добавлено.

## Адресные автоматические проверки

Тесты используют изолированную test_chatballs, штатные PostgreSQL/RLS, Django API,
application services и tenant storage. TemporaryDirectory изолирует тестовые
файлы. Контролируемые результаты транспортных вызовов существуют только внутри
автоматических тестов; отдельные mock API/HTTP-серверы не поднимались.
`--create-db` применён только после изменения схемы, далее `--reuse-db`.

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_contracts.py --tb=short --show-capture=no
```

**5 passed**: действующий v1 контракт и канонизация.

```powershell
docker compose -f compose.yaml exec -T -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_media_boundaries.py chatballs/ai/external_agents/test_runtime.py chatballs/ai/external_agents/test_runtime_control.py chatballs/ai/external_agents/test_runtime_concurrency.py chatballs/ai/external_agents/test_context_history.py chatballs/ai/external_agents/test_context_voice.py chatballs/ai/external_agents/test_send_guards.py --tb=short --show-capture=no
```

**39 passed**, 847.56s: durable runtime, PostgreSQL concurrency/RLS, FIFO/replay,
отзыв/перехват, история/голос и сериализованный native handoff.

```powershell
docker compose -f compose.yaml exec -T -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_files.py chatballs/ai/external_agents/test_reply_content.py chatballs/ai/external_agents/test_media_boundaries.py chatballs/ai/external_agents/test_config.py chatballs/ai/external_agents/test_policy.py chatballs/conversations/test_conversation_delete.py chatballs/ai/test_skill_template_security.py chatballs/i18n/tests.py::CatalogTests::test_every_language_has_the_same_keys --tb=short --show-capture=no
```

**42 passed**, 208.72s: файлы/изображения, template catalog/revisions/schema/snapshot,
смешанный batch, atomic rejection, native contact и WEB presentation, partial/
unknown/takeover, конфигурация, удаление, renderer security и ru/en каталог.

После финальной доработки файловых границ и добавления проверок усечённого
multipart/смены политики выполнен повтор на окончательном backend-образе:

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_files.py chatballs/ai/external_agents/test_media_boundaries.py --tb=short --show-capture=no
```

**14 passed**, 28.75s: ASGI chunk streaming, PNG trigger/upload, repeat/digest/
metadata, safe full download, audio/URL/20MiB rejection, interrupted storage и
truncated multipart/retry, grant только выданной истории, известный будущий ID,
source deletion, feature/policy revoke, RLS, native conversation cleanup/quota,
expiry/pinning и WEB contact на английском языке организации.

Ruff затронутых Python-файлов с `--force-exclude` успешен; migrations исключены
штатной конфигурацией. Изменённые модули проверены на NO GOD FILES: менее 300 строк,
storage/access/streaming/cleanup, rendering и batch delivery разделены.
Предупреждения тестов: существующий deprecated CheckConstraint.check и отсутствие
collectstatic в dev-образе. Полный набор тестов не запускался.

## Browser: действующее приложение

Task-local Playwright, `http://localhost:5174`, реальный backend и существующий
демо ADMIN. Демо-набор проверен read-only; seed/reset/изменений аккаунтов не было.
В штатной библиотеке открыт несохранённый черновик «Работа с заказами» и native
preview «Карточка заказа»: HTML/text, длинный список, ширины 340/300.
Реальные skills/validate и skills/preview вернули 200.

Видимый iframe: sandbox="", referrerPolicy=no-referrer; CSP default-src 'none',
style-src 'unsafe-inline', base-uri 'none', form-action 'none'. Исходящих src/href
нет; длинный snapshot прокручивается в существующем canvas без нового layout.
Измерительный iframe использует штатный allow-same-origin.

- [Штатный text preview](native-template-text.png).
- [Штатный HTML preview с длинным списком](native-template-html-long.png).

Все черновики отменены через «Не сохранять», библиотека осталась пустой.
Во время разработки наблюдались transient dev reload/WebSocket/pool ошибки;
это не выдаётся за чистую сессию. После окончательного обновления новый заход:
реальные API (session/skills/onboarding и связанные чтения) 200, console 0 errors.
Task-local browser закрыт.

Это проверка штатного общего renderer, а не работа внешнего агента с реальным
GoCoStack. Путь external result → native Message/presentation/transport проверен
отдельными автоматическими тестами. Внешние STT/LLM, мессенджеры, публичные
DNS/HTTPS и production-операции не выполнялись и не входят в условия задачи.

## C4

Владелец принял пакет `skaro-c4-335747b9-6e8e-4084-b9a6-80078086dda1`, применена
revision 43. Четыре code-external-agent-media-* и их 15 связей покрывают только
реализованные files/templates/batch/persistence, code view и две ordered dynamics.
Текущие родители сохранены; широкие будущие media/proactive/UI представления
остаются planned. Реализация planned-элементов публикуется Skaro только после
проверки точного changeHash и принятия результата задачи.
