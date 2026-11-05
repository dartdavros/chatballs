# Порталы и произвольные примеры — 05.11.2026

Добавлены 28 действий порталов: настройки, домен, виджет, категории,
статьи и версии, публикация/архивирование, импорт, файлы и опубликованный
контент с отзывами. HTTP и native используют общие application services.
Inventory содержит 259 записей подключённых API-контуров. Это ещё не полный
inventory T-175: публичный файл знаний, подключения и управление сценариями
остаются следующими частями работы.

## Backend

В backend-admin выполнен адресный прогон:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_portals.py chatballs/integrations/action_catalog/test_native_portal_files.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/support_portals/tests/test_management_api.py chatballs/support_portals/tests/test_list_pagination.py chatballs/support_portals/tests/test_public_api.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

31 passed, 2 failed (677.02 s). Две ошибки исправлены в тестах: отказ по scope
происходит до запуска; продуктовый лимит отзывов явно включается для проверки,
поскольку тестовые настройки отключают throttling. Продуктовые ограничения
не ослаблены. Повторены эти два теста вместе с затронутыми контрактами:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_portals.py::NativePortalTests::test_content_keeps_revisions_import_feedback_and_search_index chatballs/integrations/action_catalog/test_native_portals.py::NativePortalTests::test_grants_do_not_expand_scope_or_tenant_and_keep_employee_product_permission chatballs/integrations/action_catalog/test_native_skills.py chatballs/integrations/adapters/test_json_values.py chatballs/integrations/adapters/test_schema_registry.py chatballs/integrations/scenarios/test_validation.py chatballs/integrations/scenarios/test_values.py chatballs/integrations/action_catalog/test_catalog_coverage.py --reuse-db -q --tb=short
```

47 passed, 2 warnings (368.67 s). Проверены публикация и индекс, версии,
идемпотентный повтор, лимит отзывов, границы tenant/grant, сохранение/чтение/
обновление смешанных примеров навыков. Произвольные данные не превращают
вложенное поле source в привязку и не выдают право на файл. Файловая проверка
из первого прогона прошла на реальном storage, с проверкой байтов и удаления.

## Общие контролы и браузер

Доверенный контрол structured_value@1 использует поля, выбор типа и вложенные
списки из baseline constant-values.js. Обязательного JSON-редактора нет.
Журнал отображает открытые поля и смешанные списки с прежней очисткой секретов.
Содержание знаний/статей, инструкции и исходники шаблонов используют textarea@1.

```sh
docker compose exec -T frontend npm test -- src/features/integrations/scenarios/controlModel.test.tsx src/features/integrations/scenarios/model.test.ts
docker compose exec -T frontend npm run build
```

10 frontend-тестов прошли; tsc и Vite завершились успешно (4646 модулей,
Vite 4m02s, предупреждение о крупных chunks). Backend-образы и штатные
сервисы обновлены через start_environment после последних правок.
Frontend использует http://backend-app:8000; readiness через
http://localhost:20012/api/v1/health/ready/ вернул 200,
database=true, redis=true. Первый холодный переход превысил тайм-аут;
после загрузки проверка выполнена в реальном приложении без подмены API.

В браузере проверены вложенные статьи/категории, смешанный пример из
многострочного текста и числа, объект с именем поля с пробелом. Повторное
открытие шага сохранило типы и значения. Скриншоты portal-editor.png,
structured-examples.png, structured-object.png просмотрены. Черновики
закрыты через «Не сохранять», действия записи не запускались, ошибок
консоли при проверке не было. AST/Ruff прошли для 34 изменённых Python-файлов;
45 файлов кода проверены по размеру, максимум 283 строки (словари).

Это промежуточная проверка реализованной части, не приёмка всей задачи
и не публикация planned-архитектуры.
