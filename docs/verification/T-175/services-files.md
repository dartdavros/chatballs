# Сервисные подключения и файл знаний — 05.11.2026

Добавлены 9 действий управления сервисными подключениями и скачивание файла
знаний. HTTP и native используют общие management services; OAuth остаётся
отдельным протоколом. Inventory содержит 272 API-записи, включая 31 явное
исключение протоколов, и 239 исполняемых действий. Это промежуточный состав,
не полный результат T-175.

После обновления образов и сервисов через Skaro start_environment выполнено:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_services.py chatballs/integrations/action_catalog/test_native_knowledge_files.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/service_connections/test_service_api.py chatballs/integrations/service_connections/test_service_oauth.py::ServiceOAuthTests::test_start_gives_a_pkce_link_and_keeps_only_the_state_hash chatballs/integrations/service_connections/test_service_oauth.py::ServiceOAuthTests::test_callback_creates_the_connection_once chatballs/ai/tests.py::KnowledgeAttachmentTests::test_public_download_without_auth chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
docker compose exec -T frontend npm test -- src/features/integrations/scenarios/controlModel.test.tsx src/features/integrations/scenarios/model.test.ts
docker compose exec -T frontend npm run build
```

Backend: 29 passed, 18 warnings, 321.69 s. Frontend: 11 passed, 33.73 s.
Сборка tsc/Vite прошла: 4646 модулей, Vite 3m12s; прежнее предупреждение
о крупных chunks. Ruff прошёл для изменённых Python-файлов, файлов кода
свыше 300 строк в этом блоке нет, git diff --check прошёл.

Проверены tenant/роли, одноразовый аудит при повторе, переименование/пауза/
удаление, запрет выдачи секрета в результате/receipt/журнале, отказ невалидного
доступа до сети, несовместимый адаптер, чтение байтов файла из реального storage
и отказ другой организации. Регрессия штатного service API и OAuth использует
существующий unit transport fixture проекта; это не живая проверка Bitrix/OAuth
провайдера и не запуск подменного backend. В приложении подключения не создавались.

В task Playwright проверены выбор адаптера из реестра и вложенное поле доступа
с input type=password. Скриншот service-secret.png просмотрен. Проверочное
значение не являлось учётными данными; черновик закрыт через «Не сохранять».
Readiness через http://localhost:20012/api/v1/health/ready/ вернул 200,
database=true, redis=true; frontend направлен на backend-app:8000 текущей задачи.
Первый холодный переход и readiness превысили тайм-аут, после загрузки проверка
прошла без подмены окружения. Ошибок консоли не было.

Остаются транспортные/AI-подключения, разрешённое управление сценариями,
окончательный inventory и архитектурная приёмка. Этот журнал не заменяет
submit_result и не объявляет planned-архитектуру опубликованной.
