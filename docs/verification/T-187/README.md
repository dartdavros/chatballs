# T-187: конфигурация внешнего исполнения и ограниченные полномочия

Проверки выполнены 15.11.2026 в основной рабочей копии. Реализовано серверное
подмножество: opt-in организации, SERVICE/ADAPTER, настройки и явные связи,
политики, независимые ключи, сессии и монотонные разрешения, capabilities,
runtime-схемы и точная канонизация. Dispatch/callbacks/экспорт/доставка и
продуктовый UI остаются последующими задачами этапа; макеты не изменялись.

## Окружение

Использованы существующие Compose-сервисы основной копии, её PostgreSQL и Redis,
прежние данные, mount paths и секреты. Readiness настоящего backend и frontend
proxy подтвердил `database=true`, `redis=true`. Основной backend — 8010,
frontend — 5174. Работающие shared-контейнеры не пересоздавались.

Миграции применены штатным init из собранного backend-образа:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml build backend-admin
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps init
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python manage.py check
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python manage.py makemigrations --check --dry-run
```

Сборка успешна; Django check без ошибок; изменений схемы без миграций нет.
Readonly SQL основной БД после миграций: 4 организации, включённых возможностей 0;
6 агентов, builtin 6; внешних подключений 0. Аккаунты, пароли и роли основной
БД не создавались и не менялись; seed/bootstrap/reset не запускались.

## Адресные проверки

API, application services и PostgreSQL/RLS проверялись штатным Django из
собранного backend-образа в изолированной `test_chatballs`, с `--reuse-db`.
`--create-db` применялся только при изменении схемы. Все результаты capabilities
задавались на границе `GuardedTransport.send` внутри автоматического теста;
mock API, временных HTTP-сервисов и замены backend не было.

Проверенные сценарии:

- default off/builtin и включение без готового подключения;
- OWNER/ADMIN, запрет прямого выбора external при выключенной возможности;
- скрытый служебный профиль без действий сценариев и без CRM-настройки;
- одноразовый входящий ключ, verifier hash, шифрование исходящего ключа,
  отсутствие секретов в чтении и аудите;
- независимый стабильный HMAC-ключ при ротации Bearer;
- scoped credential→tenant, чужие ID, RLS и FK между организациями;
- версии режима, управления, связи, конфигурации и политики, ротация/отзыв,
  disable/re-enable, удаление/возврат связи и A→B→A;
- сохранение конфигурации при выключении, отсутствие builtin-fallback и
  отсутствие постановки builtin-хода для external;
- отдельная явно включённая помощь сотруднику через собственный builtin-провайдер;
- текущие WEB consent/form revision, отсутствие согласия другого контакта,
  раздельные sourceConnectionId/fieldId, явные шаблоны и устаревшие определения;
- несовместимые capabilities, directions/версии/required/null/закрытые структуры,
  валидные интегральные Decimal в метаданных;
- все принятые примеры и векторы канонизации, большие соседние числа,
  точные Decimal, Unicode, типизированное scoped сравнение и форматы времени;
- историческая миграция builtin с сохранением провайдера, модели, секрета,
  настроек, связей диалога и истории;
- очередь builtin, повтор доставки и гонки смены управления с доставкой.

Успешные наборы (это адресные проверки, не полный прогон):

- авторизация, PostgreSQL/RLS и историческая миграция — 9 passed;
- настройки, авторизация, контракты, согласие, политика, штатный consent,
  режим организации, активация карточки и ru/en-каталоги — 35 passed;
- контракты, запрет builtin-loop для external и независимая помощь — 9 passed;
- финальные изменения: интегральные Decimal в capabilities, авторизация,
  контракты, builtin-очередь и гонки управления — exit code 0, 20 тестов.

Команды этих наборов из корня проекта:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python -m pytest --reuse-db -q chatballs/ai/external_agents/test_auth.py chatballs/ai/external_agents/test_rls.py chatballs/ai/external_agents/test_migration.py --tb=short
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python -m pytest --reuse-db -q chatballs/ai/external_agents/test_config.py chatballs/ai/external_agents/test_auth.py chatballs/ai/external_agents/test_contracts.py chatballs/ai/external_agents/test_consent.py chatballs/ai/external_agents/test_policy.py chatballs/webchat/test_consent.py chatballs/identity/test_operation_modes.py chatballs/ai/test_agent_cards.py::AgentCardActivationTests chatballs/i18n/tests.py::CatalogTests::test_every_language_has_the_same_keys chatballs/i18n/tests.py::CatalogTests::test_placeholders_match_between_languages --tb=short
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python -m pytest --reuse-db -q chatballs/ai/external_agents/test_contracts.py chatballs/ai/external_agents/test_execution.py chatballs/ai/test_assistance_generation.py::AssistanceGenerationTests::test_real_outbox_generation_restores_values_and_has_no_conversation_side_effects --tb=short
docker compose -f compose.yaml -f compose.dev.yaml run --rm --no-deps backend-admin python -m pytest --reuse-db -q chatballs/ai/external_agents/test_config.py::ConfigurationTests::test_integral_decimal_capabilities_are_persisted_exactly chatballs/ai/external_agents/test_auth.py chatballs/ai/external_agents/test_contracts.py chatballs/conversations/test_ai_turn.py chatballs/conversations/test_operation_mode_delivery_race.py --tb=short
```

Предварительная старая проверка `identity/test_operation_mode_migration.py`
обнаружила собственный дефект: откат схемы с последующим чтением отсутствующей
`ai_aiagent.synthesis_integration_id` текущей моделью. Она не менялась;
миграцию T-187 проверяет отдельный тест с историческими моделями и восстановлением
всех актуальных leaf migrations.

В смежной проверке исправлена привязка уведомления о сбое builtin к версии
управления после собственной передачи сотруднику. Последующие смены управления
по-прежнему отсекаются. Старый тест очереди пытался получать аватар у мессенджера;
этот побочный вызов закрыт на границе тестового транспорта. Реальный GoCoStack,
внешние LLM/STT/мессенджеры и production-публикация этими тестами не подтверждаются.

## Архитектура и структура

Владелец принял пакет `skaro-c4-2e882f0c-0f38-437b-a469-11de598a474f`, revision 37.
Он выделяет `component-external-agent-settings` и узкие code-элементы; широкий
`component-external-agent`, будущие протокольные сценарии и UI сохраняются planned.
Публикация допускается только после review_c4 конкретного набора изменений.

Новые модули разделяют HTTP, команды, чтение, политику, ключи, авторизацию,
сессии, транспорт и контракты. Максимальный новый production-модуль — 134 строки;
новых компонентов UI нет. Существующий settings_base содержит только регистрацию
служебного адаптера; крупные feature/workflow файлы не добавлялись.
