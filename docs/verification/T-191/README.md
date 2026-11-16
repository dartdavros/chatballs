# T-191: инициативные сообщения и запрос сотрудника

Проверено 16.11.2026 в основной рабочей копии. Принятый вход T-190:
`608ef4f23001faf092fb2bd8a10214020af5e6cb`.

## Реализация

- POST messages и handoff используют закрытые схемы действующего OpenAPI v1 и обязательный Idempotency-Key, совпадающий с deliveryId/eventId.
- Bearer определяет организацию и подключение; agentId/authorizationId/externalSessionId проверяются по собственной текущей сессии. Организация должна явно включить возможность, внешнее исполнение должно быть готово. Выключение сохраняет конфигурацию и external-режим, но отзывает прежние полномочия без builtin-fallback.
- Инициатива допускается только в открытый диалог под ИИ с proactive=true и пустой клиентской очередью. Busy даёт 409 conversation_busy, disabled — 403 proactive_disabled. Отказ не создаёт Message/delivery/operation receipt; непринятый запрос можно повторить.
- Допуск, принятие и публикация сериализованы штатными locks организации/диалога с входящим, перехватом и передачей транспорту. Получатель, канал и организация выводятся из сохранённого диалога. Новые/закрытые диалоги не создаются/не открываются.
- Reply и инициатива используют общие normalize → accept_delivery → publish → delivery. Nullable trigger позволяет сохранить обычный FIFO checkpoint без фиктивного клиентского Message. Сохраняются все исходящие форматы, атомарная полная проверка, itemId/dedup, native snapshots, partial/unknown, проверки каждого item и запрет обгона. Очистка старого request не удаляет маршрут существующего диалога.
- Handoff входит через штатные enter_queue/record_queue_entry/notify, сохраняет группу, не назначает сотрудника. Активные/ожидающие requests отменяются, ещё не начатые items подавляются. Ключ уведомления учитывает сессию и диалог.
- Immutable tenant operation receipt содержит только identity/HMAC/ACK и post-handoff versions. Точный повтор своего handoff возвращает прежний content-free ACK при действующем credential/tenant/ownership и неизменном post-handoff состоянии; изменённое тело конфликтует. Другой отзыв, A→B→A, смена ключа/конфигурации/политики и согласия не возвращают права. Receipt не хранит summary или сообщения.
- Добавлены ai/0037 и tenancy/0088: nullable trigger, RLS/tenant FK, immutable receipt и session cleanup.

Продуктовый UI и утверждённый baseline не менялись. Browser-проверка UI для этого backend-изменения не требуется; WEB publication/команда и consent проверены штатными application services в изолированной тестовой БД. Продуктовый UI внешнего исполнения относится к T-192.

## Проверки

Штатный контур: `docker compose -f compose.yaml -f compose.dev.yaml ps`.
Backend-app healthy; PostgreSQL и Redis healthy. Реальный
`http://localhost:8000/api/v1/health/ready/` внутри backend-app вернул
`{"status":"ok","checks":{"database":true,"redis":true}}`.

Сборка:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml build backend-app
```

Успех, окончательный образ:
`sha256:4dc16e04f0ad7a3a0370e1ec33dd438c66f3cf7f9f7148a4b7e91e7a7fbd2c51`.

Целевой набор:

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_proactive.py chatballs/ai/external_agents/test_handoff_request.py chatballs/ai/external_agents/test_operation_concurrency.py chatballs/ai/external_agents/test_reply_content.py chatballs/ai/external_agents/test_runtime.py chatballs/ai/external_agents/test_runtime_control.py chatballs/ai/external_agents/test_runtime_routes.py chatballs/ai/external_agents/test_send_guards.py chatballs/ai/external_agents/test_contracts.py --tb=short --show-capture=no
```

**54 passed**, 381.19s. Покрыты: все пять исходящих форматов и смешанный batch,
WEB/SMTP, busy/disabled/closed/foreign, строгая схема/идентичность, повтор после
предварительного отказа, dedup/digest, unknown/partial/FIFO, feature disable/re-enable,
смена агента, ранний/повторный handoff, потерянный ACK, другие отзывы и независимая
ротация credential/configuration, native очередь/группа/уведомление, PostgreSQL
гонки с inbox/перехватом/send, RLS/FK/immutable receipt/session cleanup и
контрактные примеры/канонизация.

Первый запуск использовал --create-db только из-за изменения схемы; все дальнейшие —
--reuse-db. Исправлены ошибки изолированных тестовых данных (обязательные description/
contact и порядок удаления FK); продуктовые ограничения БД не ослаблялись.
После основного прогона выполнены сортировка импортов и переименование внутреннего
атрибута view в body_schema, чтобы сохранить native DRF AutoSchema.

Проверка окончательных endpoint:

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_proactive.py::ProactiveTests::test_disabled_closed_foreign_and_strict_contract chatballs/ai/external_agents/test_proactive.py::ProactiveTests::test_web_proactive_commits_native_command_after_real_consent_guard chatballs/ai/external_agents/test_handoff_request.py::HandoffRequestTests::test_early_handoff_interrupts_work_and_replays_only_content_free_ack --tb=short --show-capture=no
```

**3 passed**, 17.78s на окончательном образе.

Проверка регистрации моделей и соответствия миграций:

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python manage.py makemigrations --check --dry-run
```

**No changes detected**. Отдельный django.setup на окончательном образе подтвердил
`AutoSchema AutoSchema` для MessagesView/HandoffView. Ruff всех изменённых
runtime/test-модулей и apps.py успешен; git diff --check успешен.
NO GOD FILES: самый большой изменённый модуль — 194 строки; API, admission,
publication, handoff, persistence и тестовые helpers разделены.

Полный набор тестов не запускался. Предупреждения: существующий deprecated
CheckConstraint.check и отсутствие staticfiles в dev-образе.
Standalone verify_contract.py дополнительно пробовали запустить, но в штатном
backend-образе нет openapi_spec_validator, на host нет jsonschema, а offline uv cache
не содержит openapi-spec-validator. Этот дополнительный checker не объявляется
пройденным; неизменённый OpenAPI использован в пяти успешных runtime contract tests.

Проверки выполнялись только локально. Автоматические тесты используют изолированную
БД и контролируемые результаты вызовов штатных транспортных границ. Mock API/fake
backend/временные HTTP-серверы, seed и изменения существующих аккаунтов не
выполнялись; общие сервисы не перезапускались. Реальный GoCoStack, внешние STT/LLM,
клиентские мессенджеры, публичные DNS/HTTPS и production не проверялись и не
являются условием закрытия этой задачи по решению владельца.

## C4

Владелец принял пакет `skaro-c4-0498d365-7a8b-4908-a31a-3b8e7534d481`,
Skaro применил revision 45. Три узких planned code элемента proactive-admission,
handoff-request, operation-receipts и 11 связей покрывают эту реализацию, отдельный
code view и две ordered dynamics. Существующие context/container/component/deployment
сохранены; новых процессов/сервисов нет. Широкий component-external-agent и будущие
UI-представления не объявляются реализованными. Публикация planned элементов
выполняется Skaro после review точного changeHash и принятия результата.
