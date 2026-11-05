# Управление сценариями и финальная граница каталога — 05.11.2026

Добавлены 24 действия управления определениями, журналом, политиками агента,
справочниками, обменом и связями. Реестр содержит 274 действия; inventory —
310 точных API/transport-входов: 277 продуктовых связей и 33 протокольных входа.
Несколько методов ссылаются на одно действие, включая унаследованный GET.
Отдельная опись 24 auth-входов отличает credential-протоколы от глобального
профиля HumanUser, остающегося в T-176 принятого плана. Профиль не замаскирован
под технический login API. Варианты подтверждения/редактирования/повтора
явно перечислены как протоколы общего runner; native control — cancel/reconcile.

HTTP и native вызывают общие application services. Сохранены ревизии, tenant/RLS,
штатные права, явный делегат, поддерживаемые адаптером направления обмена,
видимость журнала и явный выбор кандидата. Definition очищается по схемам,
неизвестные входы скрываются, ключи возвращаются только как метаданные.
Сессионный editToken исключён из обычного результата журнала.

## Backend

Все команды ниже выполнялись внутри штатного `backend-admin` через
`docker compose exec -T backend-admin`; база сохранялась с `--reuse-db`.

```sh
python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short -x
```

9 passed, 1 warning (68.19 s). Проверяются реальный resolver, отсутствие
дубликатов и непривязанных API, переводы, зарегистрированные versioned controls
и совместимость их типов, а не только заранее записанное число действий.

В поведенческом прогоне прошли все 9 новых тестов из
`test_native_scenarios.py`, `test_native_run_management.py`,
`test_native_scenario_policies.py`, `test_native_entity_links.py`, все 3 теста
`scenarios/test_configuration_api.py` и проверки RunAPITests
`test_catalog_rejects_unknown_conversation_before_exposing_file_names`,
`test_detail_lists_only_controls_authorized_in_current_state`,
`test_employee_cannot_read_organization_journal_or_control_unrelated_run`.
Итог до остановки: 15 passed, 1 failed (375.14 s). Падение следующей проверки
было старым patch-путём `launch_views.default_registry`; сервис вынесен в
`manual_catalog_queries`. Исправлены patch-пути в test_api/test_deferred_sources.

Адресный завершающий прогон:

```sh
python -m pytest chatballs/integrations/execution/test_api.py::RunAPITests::test_paused_connection_is_shown_unavailable_without_sending chatballs/integrations/execution/test_api.py::RunAPITests::test_preview_has_no_run_and_changed_confirmation_cannot_send chatballs/integrations/execution/test_api.py::RunAPITests::test_runtime_journal_and_details_do_not_disclose_other_tenants chatballs/integrations/execution/test_ai_scenarios.py::AgentScenarioTests::test_policy_api_is_explicit_atomic_and_checks_revision chatballs/integrations/scenarios/test_synchronization_runtime.py::ExchangeRuntimeTests::test_link_search_requires_explicit_candidate_and_current_revision chatballs/integrations/scenarios/test_synchronization_runtime.py::ExchangeRuntimeTests::test_search_no_results_keeps_existing_link chatballs/integrations/scenarios/test_synchronization_runtime.py::ExchangeRuntimeTests::test_runtime_rls_hides_foreign_link chatballs/integrations/execution/test_deferred_sources.py::DeferredSourceTests::test_deferred_input_is_disabled_in_catalog_and_launch chatballs/integrations/action_catalog/test_auth_boundary.py --reuse-db -q --tb=short -x
```

9 passed, 9 warnings (154.91 s). Предыдущая сессия с потерянным итоговым выводом
не засчитана; приведён результат повторного завершённого запуска.
Предупреждения: существующий deprecated CheckConstraint и отсутствие staticfiles.

В первом прогоне этого блока также исправлены два ошибочных тестовых ключа
`chatballs:…`, устаревшее ожидание числа inventory и тест обмена: сначала
проверяется запрет неподдерживаемой условной записи, затем поддерживаемое
направление reverse. Продуктовый запрет не ослаблен. Проверены CRUD/replay,
отказы прав, маскирование секрета/ключа, атомарный откат политик по ревизии,
изоляция журнала и retention с подтверждением сокращения и отсрочкой 24 часа.

## UI и сборка

```sh
docker compose exec -T frontend npm test -- src/features/integrations/scenarios/controlModel.test.tsx src/features/integrations/scenarios/model.test.ts
docker compose exec -T frontend npm run build
```

11 passed (57.16 s). tsc и Vite: exit 0, 4647 модулей, 3m20s;
существующее предупреждение о крупных chunks. Backend-образы собраны штатным
start_environment. После завершающей сортировки импортов двух тестовых файлов
окружение повторно сверено через Skaro. Миграций в этой части нет.

Task-local Playwright, существующая демо-учётная запись ADMIN. Frontend 20012
использует backend-app:8000 этой задачи; readiness вернул database=true,
redis=true. В действии создания сценария открыт scenario_settings@1,
использующий прежние ScenarioSections/ScenarioDrawer. Добавлен триггер ИИ,
выбраны агент «Приёмная» и режим «С подтверждением». После закрытия/повторного
открытия значения сохранились. Скриншоты [редактора](scenario-settings-editor.png)
и [значения](scenario-settings-value.png) просмотрены; геометрия устойчива.
Финальная проверка: 0 console errors, 1 warning. Несохранённый собственный
черновик закрыт через «Не сохранять». Предыдущие тайм-ауты во время autoreload
не засчитаны как успешная проверка.

Ruff, git diff --check и размер изменённых модулей проверены; файлы разделены
по схемам, адаптерам, сервисам, запросам и UI. Новых макетов или веток ядра
по имени действия нет. Пароли/роли/доступы существующих аккаунтов не менялись,
seed и временные HTTP-серверы не запускались. Реальные внешние провайдеры
не объявляются проверенными этим набором адресных тестов.

Справка и примеры: [ru](../../native-scenario-actions.ru.md),
[en](../../native-scenario-actions.en.md). Принятие результата и публикация
определяются ответами C4/submit_result, а не этим журналом.
