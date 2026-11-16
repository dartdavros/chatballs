# T-188: устойчивый текстовый ответ внешнего исполнителя

Проверки выполнены 16.11.2026 в основной рабочей копии относительно принятого
кода T-187 `39089a7c5ca014f9af9de13b0db695086323bc51`.
Реализован текстовый цикл inbox → request → receipt → delivery → recovery.
Расширенный контекст, медиа, STT, инициатива и продуктовый UI этой проверкой
не объявляются реализованными. Неподдерживаемые данные отклоняются до dispatch.

## Штатное окружение и сборка

Использованы существующие Compose, PostgreSQL и Redis основной копии.
Работающие shared-сервисы не пересоздавались; пути, volumes и аккаунты не менялись.
Новый backend-образ собран штатной командой (SHA256
`9e0aa26414dc163b7615bd12a0a069b995778fcf89ef35167c6a5ef5551ebb27`).

```powershell
docker compose -f compose.yaml -f compose.dev.yaml build backend-admin
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps init
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python manage.py check
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python manage.py makemigrations --check --dry-run
```

Сборка успешна; check: 0 issues; makemigrations: No changes detected.
Init применил ai.0033–0035 и tenancy.0083–0084. Настоящий backend на 8010:
`GET /api/v1/health/ready/` вернул `database=true`, `redis=true`.
Readonly SQL основной БД: 4 организации, внешнее исполнение включено у 0,
внешних подключений 0. Вызовов внешнего исполнителя из основной БД не было.

HTTP исполнителя, включая передачу запроса и ожидание ответа, выполняется вне
транзакции состояния. Проверка непосредственно перед передачей открывает и
закрывает короткую транзакцию. Передача сообщения клиентскому native транспорту
сериализована со сменой управления в штатном порядке organization → conversation.
Срок запроса, lease/fence и полномочия перепроверяются на границе транспорта.

## Сценарии и конкуренция

Использована только изолированная `test_chatballs` на настоящем PostgreSQL,
штатные API/application services/outbox handlers и контролируемые результаты
на границах HTTP/SMTP/native транспорта внутри автоматических тестов.
Mock API, временные HTTP-серверы и внешние сервисы не запускались.
`--create-db` применён при изменении схемы; последующие прогоны — `--reuse-db`.

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_runtime.py chatballs/ai/external_agents/test_recovery.py chatballs/ai/external_agents/test_runtime_control.py chatballs/ai/external_agents/test_runtime_routes.py chatballs/ai/external_agents/test_runtime_concurrency.py chatballs/ai/external_agents/test_send_guards.py chatballs/ai/external_agents/test_protocol_recovery.py --tb=short --show-capture=no
```

Результат: **39 passed**, 519.63s. Единственное предупреждение — существующий
deprecated `CheckConstraint.check` в identity migration 0007.

После проверки ограничения JSON вынесен общий serializer страницы истории:
до dispatch каждый элемент проверяется на возможность выдачи без усечения.
Добавлены три сценария: слишком большой trigger, неделимый большой элемент
истории и пагинация больших текстов без потери содержимого. Повторяются только
они и непосредственно затронутые сценарии контекста/FIFO/callback:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_runtime_limits.py chatballs/ai/external_agents/test_runtime.py chatballs/ai/external_agents/test_runtime_control.py::RuntimeControlTests::test_history_snapshot_excludes_trigger_future_and_internal_records --tb=short --show-capture=no
```

Результат: **10 passed**, 115.62s (три новых и семь повторных адресных проверок).
Дополнительно код отказа неподдерживаемому формату callback приведён к
контрактному 422 `unsupported_content`; unknown/cancelled остаются невалидными
TerminalResult (400). Повреждённый HTTP-ответ использует прежний requestId и
транспортный retry; ошибку best-effort cancel нельзя принять за terminal.
Чрезмерный Retry-After ограничивается до построения timedelta.

Одиночный dev-прогон остановлен из-за ожидания Windows bind mount
(`p9_client_rpc`, disk sleep). Итоговая проверка выполнена каноническим Compose
из того же штатного backend-образа без source mount, с теми же dev DEBUG/CLOUD,
секретами, PostgreSQL и Redis. Общие сервисы не менялись. Включены актуальные
проверки recovery, guards, отказа формату и транзакционной границы:

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_protocol_recovery.py chatballs/ai/external_agents/test_send_guards.py chatballs/ai/external_agents/test_runtime_control.py::RuntimeControlTests::test_unknown_cancelled_and_unsupported_outcome_are_not_terminal_results chatballs/ai/external_agents/test_runtime_concurrency.py::RuntimeConcurrencyTests::test_network_boundaries_have_no_transaction_and_callback_may_win_post --tb=short --show-capture=no
```

Результат: **11 passed**, 80.55s. Предупреждения: прежний CheckConstraint.check
и отсутствующий staticfiles в dev backend-образе без collectstatic.
Всего проверено 43 различных сценарных/конкурентных теста, с адресными повторами
после изменений. Новый broker, БД или обязательный контейнер не добавлялись.
Два пустых неиспользуемых default volumes, созданных canonical Compose,
удалены после проверки; существующие volumes не затронуты.

| Критерий | Проверенное поведение |
|---|---|
| 1 | Реальный ingest/outbox; постоянный ID, зашифрованные SQL payloads, immutable DB guards; текстовая история; отказ расширенной политике/форматам. |
| 2 | FIFO с будущим trigger, предыдущим ответом в следующем контексте; два конкурентных worker получают одну голову; отдельные jobs штатного outbox. |
| 3 | Sync, 202, GET-only polling, callback до 202, потеря ответа, restart, lease/fencing; вызовы и callbacks проходят общую машину. |
| 4 | Один receipt/Message при конкурентном callback; точный ACK повтора; конфликт result/session/text → 409; unknown/cancelled не TerminalResult; cancel сохраняет terminal. |
| 5 | Failed и structured handoff без фиктивных Message/delivery; штатная очередь и уведомление группе, private summary; HANDOFF_TOKEN остаётся текстом. |
| 6 | Несколько ordered items/Message без ai_reply_to; WEB accepted, SMTP failed, durable sending → unknown; unknown не повторяется и блокирует обгон. |
| 7 | Scoped delivery GET требует authorizationId; WEB consent до public row; повторные проверки перед фактическими HTTP/SMTP/native передачами. |
| 8 | Human/assignment/close/archive/feature/credentials/configuration/consent отзывают старую работу; поздний callback suppressed; старый ключ 401, чужая связь 404; возврат выдаёт новое разрешение. |
| 9 | Default 120s, HTTP 10s, long >24h, retry 1/5/15, polls 5/15/30/30, Retry-After ограничен deadline; unknown сверяется GET без нового ID. |
| 10 | Активные payloads защищены; 7/30 cleanup; повтор после очистки возвращает ACK; повтор trigger не создаёт новую работу; archive/delete удаляют payload, HMAC tombstone остаётся. |
| 11 | PostgreSQL/RLS всех пяти таблиц, tenant FK, гонки worker/callback/takeover; проверки только затронутых сценариев и backend build. |

## Адресная регрессия

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_config.py chatballs/ai/external_agents/test_policy.py chatballs/ai/external_agents/test_contracts.py chatballs/ai/external_agents/test_auth.py chatballs/ai/external_agents/test_execution.py chatballs/ai/external_agents/test_consent.py chatballs/conversations/test_ai_turn.py chatballs/conversations/test_operation_mode_delivery_race.py chatballs/conversations/test_email_smtp_outcomes.py chatballs/conversations/test_email_agent_independence.py chatballs/i18n/tests.py --tb=short --show-capture=no
```

Результат: **58 passed, 1 skipped**, 572.15s. Штатно пропущена проверка ключей
frontend из backend-контейнера: frontend там не смонтирован; UI не менялся.
Backend-каталоги ru/en и ключи использованных строк проверены успешно.
Полный набор тестов не запускался. Ruff и проверка размера изменённых модулей
успешны: самый большой внешний модуль — 190 строк, изменённые файлы ≤300 строк.

## C4 и границы результата

Проверено принятое узкое покрытие revision 39: шесть `code-external-agent-text-*`,
их проверенные связи и расширение settings API ordinary/long. Общий
`component-external-agent`, будущие контекст/форматы/инициатива/UI и broad views
остаются planned. Связь `rel-external-agent-text-network` тоже остаётся planned,
пока её общий endpoint `code-service-adapter-network` не verified в своей области.
Существующие родители не объявляются полностью реализованной будущей функцией.

Протокол проверен на изолированных границах без реального GoCoStack, внешних
LLM/STT, мессенджеров, публичных DNS/HTTPS или production-операций. Работа
приложения с реальным сервисом заказчика этим отчётом не заявляется.
