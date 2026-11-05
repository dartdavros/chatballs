# Транспортные/AI-подключения и файлы виджета — 05.11.2026

Добавлены 11 действий connections.*: список, создание/изменение/удаление,
проверка, обновление инструментов, подтверждение/отзыв чтения, проверка адреса,
загрузка и скачивание изображения виджета. HTTP и native вызывают общие
management/asset services. Публичное скачивание ассета, ранее исключённое
из контура общения T-174, теперь имеет исполняемое действие в контуре контента.
Inventory: 282 API-записи, 30 протокольных исключений, 250 native-действий.

После сборки backend-образов и обновления всех штатных сервисов через
Skaro start_environment выполнено:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_connections.py chatballs/integrations/action_catalog/test_native_widget_files.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/test_proxy_masking.py chatballs/integrations/test_external_server.py chatballs/integrations/test_external_server_headers.py chatballs/integrations/test_address_validation.py chatballs/webchat/test_widget_assets.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

53 passed, 33 warnings, 346.17 s. Проверены сохранение ключа/прокси при правке,
очистка секретов до результата/receipt, одноразовый аудит при повторе, роль,
grant/scope/tenant, явное confirmed для инструмента, отзыв подтверждения,
отказ неверной конфигурации, очистка SVG, storage, файловое владение шага,
удаление изображения вместе с подключением и регрессия HTTP-контрактов.
Новые тесты не запускают подменные HTTP-серверы. Существующие unit-проверки
адресов используют подмену DNS, проверка S3 — существующий unit-fixture;
это не свидетельство живой проверки внешнего сервера или S3.

В task Playwright http://localhost:20012 проверены новое действие, вложенные
настройки внешнего сервера и список заголовков. connection-editor.png просмотрен.
Черновик закрыт через «Не сохранять»; реальные подключения не создавались,
учётные записи и права не менялись. Ошибок консоли не было. Readiness через
frontend вернул 200, database=true, redis=true; используется backend-app:8000
текущего окружения. UI-код в этом блоке не менялся; предыдущая сборка UI
остаётся действующей. Новые backend-образы собраны Skaro перед проверкой.

Ruff, git diff --check и проверка размера изменённых файлов прошли.
Управление сценариями, итоговый inventory и C4-приёмка остаются следующими
частями T-175. Этот отчёт не объявляет всю задачу или этап завершёнными.
