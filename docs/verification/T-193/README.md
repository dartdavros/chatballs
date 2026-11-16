# T-193 — исправления внешнего исполнения

Дата: 2026-11-16. Проверяется сторона Chatballs. Владелец в этом чате прямо
исключил требование browser-проверки селектора из приёмки T-193 и запретил
фиксировать отсутствие внешней связи как blocker. Остальные проверки сохранены.
Фактически не выполненная browser-проверка селектора не заявляется выполненной.

## Основание и воспроизведение

- Release workflow использует `apps/backend/Dockerfile.production` с контекстом
  корня репозитория. В исходном Dockerfile отсутствовал COPY контрактов, тогда
  как runtime использует `/app/packages/contracts/external-agent-v1`.
- До исправления регрессия `test_retention_visibility.py` показала попадание
  suppressed ID в публичную страницу после перехвата → возврата ИИ → нового
  клиентского хода. Отдельный прогон границ retention показал возвращение
  suppressed Message в `Message.objects` после удаления request/delivery/items.
  Первая попытка проверки поиска имела ошибочный lookup теста; он заменён на
  штатный `conversation_list`, после чего воспроизведён именно дефект cleanup.
- До исправления ProcessingCard менял только три срока; `emptyBinding` задавал
  ordinary, а state/proactive выбирали срок только по processing_mode. Long
  timeout оставался недостижимым через форму.
- Принятый REST-66e46e103944410c/S20 содержит три числовых поля и инициативу,
  но не выбор режима. В этой задаче владелец через структурированный вопрос
  выбрал «Выбор режима»: существующий SelectField перед сроками, «Режим обработки»
  с вариантами «Обычный запрос» / «Долгая обработка», ru/en. Это единственное
  явно принятое дополнение baseline; другие состояния и компоновка не менялись.

## Изменения

Production-Dockerfile копирует весь локальный каталог контрактов по runtime-пути.
Внешний контракт, его примеры и YAML-модули не менялись.

DeliveryItem атомарно сохраняет факт state/initiative/sequence/position в
существующем приватном Message.ai_delivery. JSON merge сохраняет остальные
ключи, включая externalFileId. Факт живёт столько же, сколько сообщение.
Перед удалением operational metadata cleanup также переносит факты старых
записей, созданных до исправления. Переписка не удаляется ради скрытия.

Общий фильтр исключает suppressed по постоянному факту и по ещё существующему
DeliveryItem. Он используется default manager, новым снимком истории и каждой
страницей уже сохранённой истории. После cleanup порядок остаётся привязан к
исходному ходу/позиции; UI сохраняет настоящий статус accepted/unknown/failed,
а исчезновение DeliveryItem не выдаётся за отправку. Тестовая переписка остаётся
изолированной; её проекция тоже читает сохранённый факт.

SelectField меняет processingMode существующего draft и штатного атомарного
configuration command. Серверные правила выбора и фиксации deadline не менялись.
Новые системы, процессы, полномочия, fallback и изменения схемы БД не добавлялись.

## Проверки

Команды выполняются из корня проекта. Используются основной Compose, реальные
PostgreSQL/Redis и существующий backend-admin; pytest использует изолированную
тестовую БД и `--reuse-db`. `--create-db`, seed и reset не запускались.

Подтверждены readiness через `http://localhost:8010/api/v1/health/ready/` и
frontend-прокси `http://localhost:5174/api/v1/health/ready/`: database=true,
redis=true. `manage.py migrate --check` — exit 0; `manage.py check` — без замечаний;
`manage.py makemigrations --check --dry-run` — No changes detected.

Целевые команды:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T backend-admin python -m pytest --reuse-db -q chatballs/ai/external_agents/test_retention_visibility.py
docker compose -f compose.yaml -f compose.dev.yaml exec -T backend-admin python -m pytest --reuse-db -q -x chatballs/ai/external_agents/test_processing_settings.py chatballs/ai/external_agents/test_context_history.py chatballs/ai/external_agents/test_recovery.py chatballs/ai/external_agents/test_runtime_control.py chatballs/ai/external_agents/test_reply_content.py chatballs/ai/external_agents/test_proactive.py chatballs/ai/external_agents/test_test_scope.py chatballs/ai/external_agents/test_send_guards.py
docker compose -f compose.yaml -f compose.dev.yaml exec -T frontend npm --prefix /app run test --workspace @chatballs/internal-ui -- src/features/settings/external-agent/bindings.test.ts src/features/conversations/externalFeed.test.tsx src/i18n/catalog.test.ts --maxWorkers=1 --no-file-parallelism
docker compose -f compose.yaml -f compose.dev.yaml exec -T frontend npm --prefix /app run test --workspace @chatballs/internal-ui -- src/features/settings/external-agent/ProcessingCard.test.tsx --maxWorkers=1 --no-file-parallelism
docker compose -f compose.yaml -f compose.dev.yaml exec -T frontend npm --prefix /app run build
docker compose -f compose.yaml -f compose.dev.yaml build backend-app
docker build -f apps/backend/Dockerfile.production -t chatballs-backend:t193-production .
docker run --rm --network none -e CHATBALLS_SECRET_KEY=t193-offline-contract-check -e CHATBALLS_DEBUG=false -e CHATBALLS_ENV=production chatballs-backend:t193-production python -m pytest --reuse-db -q chatballs/ai/external_agents/test_contracts.py
```

Результаты: новые retention-сценарии — 3 passed; UI/i18n — 8 passed,
ProcessingCard — 1 passed. Штатная frontend-сборка — exit 0, 4672 модуля,
обычное предупреждение о размере chunk; backend dev-сборка — exit 0.
Первый production-образ `sha256:0c43c84b728695b3540966dbe2a6506925ce00009610c90bdecb31f075c66ad0`
(934452401 байт, USER hub) прошёл 5 contract tests без сети и mounts.
В нём загружены все 13 YAML-модулей; external_agent_contract_missing отсутствует.
Финальная пересборка — exit 0, образ
`sha256:63424186b6e540a723257d15701f957b19bcd834e61490c7fa46603e20b4fc63`.
Тот же offline contract command — **5 passed, 3.15 s**. Загрузка registry и
сравнение SHA256 всех 13 YAML с рабочими источниками выполнены отдельным
`docker run --rm --network none ... python -c ...`; совпадают все имена/байты.

Основной целевой набор (processing_settings, context_history, recovery,
runtime_control, reply_content, proactive, test_test_scope, send_guards) —
**50 passed, 197.30 s**. Новые retention-тесты — **3 passed** в предыдущем
наборе; после упрощения helper legacy-сценарий отдельно повторён:
**1 passed, 33.69 s**. Единственное backend-предупреждение — ранее существующее
Django CheckConstraint.check в миграции identity. Во время подготовки нового
deadline-теста была исправлена его тестовая externalSessionId: после первого
ответа сохраняется session-1, а не null. Runtime-контракт не изменён.

Проверены ordinary=120, long=7200, maximum=3600 с отказом 7200>3600,
сохранение/GET той же команды формы, возврат ordinary, неизменность deadline
при retry/202/processing и изменении настроек. Существующая recovery-регрессия
проверяет long=172800 без жёсткого 24-часового потолка. Перехват и возврат ИИ
в новых тестах выполняются штатными control services. История проверяется
inline и всеми GET-страницами по 3 сообщения: ID, порядок, удаление, отсутствие
trigger/будущих/системных записей; сохранение порядка после metadata cleanup.
Непосредственно проверены лента, visible_message, полнотекстовый conversation_list,
клиентский session_messages, ACK/dedup/tombstone и отсутствие повторной отправки.

Финальный `npm --prefix /app run typecheck --workspace @chatballs/internal-ui`
в штатном frontend-контейнере — exit 0, включая добавленные тесты.
Ruff всех изменённых Python-файлов — чисто. NO GOD: изменённые кодовые файлы
меньше 180 строк; UI использует существующий компонент поля, draft и команду
сохранения; фильтр общий для публичных чтений. Схемы/миграции не менялись.

## Браузер и границы доказательства

Skaro Playwright: настоящий `localhost:5174`, вход существующим демо-ADMIN из
документированного demo manifest. Открыт штатный экран `/settings/external`.
GET настроек — 200, enabled=false, connections=[], в каталоге 5 агентов.
В этом состоянии ProcessingCard отсутствует; добавление связи отключено до
совместимого подключения. Селектор в браузере не проверен; это требование снято
прямым указанием владельца, SSR-тест не выдаётся за browser-проверку.
Вкладка закрыта. Конфигурация организации и агентов не менялась.

Backend-исправления и регрессии зафиксированы коммитом
`eda181225ce8913d9a2c028128791846c499f559` в `skaro/t-193-external-audit` поверх
принятого T-192 `c822fdfef4f6ee4454469126879dd1f385d6d56e`. Отдельный Git index
сохранил текущую main, индекс и остальные незакоммиченные изменения основной
копии. Дополнение UI и отчёт фиксируются отдельным следующим коммитом.

Mock API/fake backend, временные HTTP-серверы, фиктивные capabilities и
проверочные данные в общей БД не создавались. Учётные данные, роли и переписка
не менялись. Сервисы не перезапускались и не пересоздавались; сборка образа
не заменяет образ уже работающих контейнеров. Cleanup реальной переписки не
запускался: его поведение проверяется в изолированной тестовой БД.

Реальная приёмка GoCoStack/STT/LLM/клиентских каналов, production-развёртывание,
публикация образа и выпуск релиза не выполнялись и не заявляются.
