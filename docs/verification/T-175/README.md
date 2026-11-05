# T-175: журнал адресной проверки

Дата: 2026-11-05. Ниже сохранена история адресной проверки по частям.
Итоговый каталог и проверка сценариев описаны в [завершающей части](scenarios.md).

## Основание и окружение

Личная приёмка обоих baseline зафиксирована в принятой SPEC-0037 R-28
поручением владельца от 22.10.2026. Повторной приёмки этих макетов не требуется.

Штатное окружение Skaro: `skaro-chatballs-t-175`, frontend `http://localhost:20012`,
backend-app `http://localhost:20010`, backend-platform `http://localhost:20011`.
Frontend использует `VITE_DEV_API_TARGET=http://backend-app:8000`.
`/api/v1/health/ready/` через frontend возвращает database=true и redis=true.
PostgreSQL, Redis, backend-app, backend-platform, backend-admin, frontend,
web-chat, worker и worker-events запущены штатной командой Skaro.
Образы собирает `start_environment`; миграции выполняет штатный init.
Никакие seed, подмены API, изменения существующих паролей или ролей не выполнялись.

## Группы, доступность и категории знаний

Коммит `82aad74f`: 13 действий, общий реестр содержит 168 записей inventory
(включая ранее классифицированные протоколы).

Запущено внутри backend-admin:

```sh
python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_groups.py chatballs/integrations/action_catalog/test_native_availability.py chatballs/identity/test_supervision.py chatballs/identity/test_work_status_api.py chatballs/identity/test_work_status_supervision.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

Результат: 36 passed, 1 failed. Единственное падение — устаревшее ожидание
заблокированного сотрудника: существующая policy возвращает также
`reportCapabilities: []`. Ожидание уточнено без изменения политики прав.
Затем запущены категории знаний и непосредственно исправленная проверка:

```sh
python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_knowledge_categories.py chatballs/ai/test_knowledge_category_api.py chatballs/identity/test_supervision.py::SupervisionTests::test_scope_never_grants_global_admin_access_and_blocking_removes_effective_area chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
python manage.py check
```

Результат: 15 passed; system check — 0 issues. Ruff по всем изменённым Python
файлам и `git diff --check` прошли. Изменённые модули меньше 300 строк.

Browser-проверка через task-local Playwright, существующая демо-учётная запись
ADMIN из документированного манифеста. Создан сценарий
`T-175 — проверка чтения групп` (`e436ed41-a0e8-4a09-a739-60d6d4b155a9`):
один шаг `groups.get`, область организации, ручной доступ только проверяющей
сотруднице. Общий редактор показал новые действия и локализованные поля.
Ручной запуск из диалога №1 завершился успешно:
`2f4182de-8665-4cab-b768-2d6401b5c406`. Общий журнал показал обе существующие
группы, участников, цвета, количество сотрудников и даты создания.
Сценарий не отправлял сообщений и не изменял группы.

Скриншот: [результат чтения групп](groups-run.png).
На странице чата наблюдались существующие ошибки HTTP 409 запросов email/options
и предупреждение о повторяющемся React key; при пересборке были временные ошибки
соединения. Поэтому проверка не означает отсутствия всех ошибок приложения.
API сценария и чтения результата вернули 200/201, сам шаг имеет состояние «Успешно».

## Знания, импорт, файлы и массовые операции

Добавлены ещё 13 действий; inventory теперь содержит 181 запись. Изменены
штатные HTTP views: они вызывают те же application services, что и действия.
CRUD знаний, импорт, переиндексация и вложения объявлены I/O с retry=NONE:
индексация может вызвать провайдера, а файловые операции меняют хранилище.
Подтверждённый результат сохраняется обычной native receipt; неоднозначный
сбой не объявляется безопасным для повторения. Массовые привязки и перенос
категории остаются локальными транзакционными командами.

```sh
python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_knowledge.py chatballs/ai/test_knowledge_api_v2.py chatballs/ai/test_knowledge_list.py chatballs/ai/test_knowledge_detail_payload.py chatballs/ai/test_knowledge_policy_api.py chatballs/ai/test_knowledge_import_v2.py chatballs/ai/test_knowledge_bulk.py chatballs/ai/test_agent_attachments.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

Первый прогон: 54 passed, 1 failed. Новая проверка отсутствия материала ошибочно
смотрела всю тестовую БД, где намеренно оставлен материал чужой организации.
Она уточнена фильтром текущей организации и проверкой сохранности чужой записи.
Прикладные guards в этом тесте уже вернули ожидаемое состояние failed.
Повторный прогон проверки прав прошёл. Новый тест вложений обнаружил ошибку
в самом тесте: чтение tenant-хранилища вне tenant_atomic. Проверка перенесена
в контекст организации; прикладной код загрузки и удаления не менялся.

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_knowledge.py::NativeKnowledgeTests::test_foreign_target_and_granted_employee_still_cannot_manage_knowledge chatballs/integrations/action_catalog/test_native_knowledge_files.py --reuse-db -q --tb=short
```

После повторного успешного `start_environment` 05.11.2026 запущен:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_knowledge_files.py --reuse-db -q --tb=short
```

Результат: 1 passed (58.12 s). Проверены байты файла, извлечённый текст,
индексация, удаление записи и физического файла через штатное хранилище.
Frontend readiness вернул 200 с database=true и redis=true. Каталог и список
сценариев в браузере получили 200; связь восстановилась после загрузки.

`python manage.py check` — 0 issues. Ruff и разбор AST прошли; новые модули
и изменённые views разделены по чтению, командам, схемам и обёрткам, меньше 300 строк.

После успешной пересборки штатного окружения в браузере открыты каталог и форма
«Создать материал базы знаний»: видны заголовок, описание, содержимое, включение,
категория и общие источники значений/преобразования. API catalog/list вернули 200.
Скриншот: [форма действия знаний](knowledge-editor.png).
Черновик проверки закрыт без сохранения и запуска записи в реальную базу.
На этой странице ошибок console не наблюдалось; это не проверка всего приложения.

## Сотрудники, приглашения и передача владения

Добавлены 12 действий: список/карточка/фото, создание, изменение, восстановление
доступа по почте, отзыв сессий, блокировка/разблокировка, владение и приглашения.
Inventory содержит 193 API-записи. Одноразовая выдача пароля классифицирована
как вариант протокола аутентификации; шаги используют письмо и не возвращают
пароль. Исходные HTTP-формы сохраняют прежние режимы.

HTTP views и native-обёртки вызывают общие application services. Подтверждённый
отказ сохраняет доменный аудит и failed-receipt без данных результата; старые
receipt без поля state по-прежнему читаются как completed.

После успешного `start_environment`:

```sh
python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_employees.py chatballs/integrations/action_catalog/test_native_failed_result.py chatballs/integrations/action_catalog/test_native_io.py chatballs/integrations/action_catalog/test_native_comments.py chatballs/identity/test_employee_password.py chatballs/identity/test_employee_list.py chatballs/identity/test_employee_invitation.py chatballs/identity/test_administration_api.py chatballs/identity/test_supervision.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

79 passed, 2 failed (408.35 s). Исправлены повреждённые русские подписи и
сериализация роли после передачи владения: TextChoices приводится к строке в
общем employee_payload. Права и сам переход владения не менялись. Диагностический
повтор подтвердил `employee.role: choice`; 9 остальных проверок прошли.
После исправления и новой успешной сборки:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_employees.py::NativeEmployeeTests::test_multi_org_password_and_admin_ownership_transfer_remain_forbidden chatballs/integrations/action_catalog/test_native_failed_result.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/identity/test_supervision.py::SupervisionTests::test_transfer_of_ownership_clears_previous_supervision chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

14 passed (66.05 s). `manage.py check` — 0 issues; Ruff и AST прошли, все 28
новых/изменённых Python-модулей этой части меньше 300 строк.

В штатном браузере проверена форма «Добавить сотрудника с доступом по почте»:
почта, имя, телефон, должность, роль и группы; поля пароля нет. Выбор постоянной
роли показывает администратора, супервизора и сотрудника, без владельца.
Подписи исправлены и повторно прочитаны из DOM. Скриншот компоновки просмотрен:
[форма сотрудника](employee-editor.png). Черновик не запускался; существующие
учётные записи, пароли и роли не менялись. В открытой во время сборки вкладке
зарегистрированы ошибки соединения; они не объявляются отсутствующими.

Справка и примеры: [ru](../../native-organization-actions.ru.md),
[en](../../native-organization-actions.en.md).

## Настройки организации

Добавлены 13 действий: настройки и режим организации, логотип, аудит,
персональное начало работы, голосовые/звонки и состояние/задания демо-набора.
Inventory содержит 206 API-записей, реестр — 176 исполняемых действий.
Установка и удаление демо-набора при проверке не запускались.

После успешного `start_environment` выполнено:

```sh
python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_settings.py chatballs/integrations/action_catalog/test_native_settings_files.py chatballs/identity/test_administration_api.py::AdministrationApiTests chatballs/identity/test_logo_svg.py chatballs/identity/test_operation_modes.py chatballs/conversations/test_chat_extras.py::OnboardingTests chatballs/conversations/test_voice_ai_and_features.py::CommunicationSettingsTests chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

47 passed, 32 warnings (502.25 s). Проверены штатные HTTP-сценарии, переход
режима очереди, запрет повышения прав через grant, откат смешанного списка
с чужим подключением, скрытие паролей и секретов до receipt, реальное хранилище
логотипа. `manage.py check` — 0 issues. Ruff, AST и `git diff --check` прошли;
изменённые Python-модули этой части не превышают 300 строк.

В браузере открыта форма «Изменить настройки организации», проверены поля
имени, часового пояса, языка и выбор режимов «Агенты ИИ»/«Только операторы».
[Скриншот формы](settings-editor.png) просмотрен; черновик закрыт без сохранения
и запуска. Каталог и список сценариев до следующей сборки вернули HTTP 200.
Во время пересборки зафиксированы 4 ошибки соединения и 1 предупреждение;
отсутствие ошибок всего приложения не заявляется.

После этих проверок фильтр периода аудита уточнён: часовой пояс берётся явно
из организации, в том числе вне HTTP-запроса. Добавлена адресная проверка
`chatballs/identity/test_audit_period.py`. При следующем `start_environment`
готовность frontend-прокси не подтвердилась. Прямой `/api/v1/health/ready/` backend вернул 200,
database=true и redis=true; запросы через frontend превысили 15/20 секунд,
в его журнале наблюдался `getaddrinfo EAI_AGAIN backend-app`.
Повторный `start_environment` завершился ошибкой:
`The environment is not ready at http://localhost:20012/api/v1/health/ready/: The operation was aborted due to timeout`.
Контейнеры backend были пересозданы во время этого запуска; промежуточные
старые записи `compose logs` не являются подтверждением новой сборки.
Адресный повтор `python -m pytest chatballs/identity/test_audit_period.py chatballs/identity/test_administration_api.py -k audit --reuse-db -q --tb=short`
запущен в backend-admin после его пересоздания: 9 passed, 15 deselected,
9 warnings (164.64 s). Исправление часового пояса и фильтры аудита проверены.
Последний блок настроек остаётся незакоммиченным и не предъявляется как готовый.

## Агенты: промежуточная проверка 05.11.2026

Добавлены 12 действий агентов, включая тестовый чат, с общими доменными
операциями для HTTP и сценариев. Inventory содержит 218 API-записей.
Фоновые native-действия выбирают язык инициатора; внутренняя ошибка демо-задания
не возвращается как обычное поле результата.

Первый повтор `start_environment` подтвердил готовность среды. После добавления
агентов следующий запуск вновь завершился тайм-аутом frontend readiness:
`The environment is not ready at http://localhost:20012/api/v1/health/ready/: The operation was aborted due to timeout`.
Прямой запрос из frontend-контейнера к `backend-app:8000` вернул 200 с
`database=true`, `redis=true`; запрос к Vite на 5173 превысил 10 секунд.
У четырёх фоновых потоков Vite наблюдались ожидания `d_alloc_parallel` и
`p9_client_rpc`. Процесс pytest также ожидал `p9_client_rpc`; PostgreSQL
тестовой базы — `DataFileImmediateSync`. Это наблюдения, а не доказательство
единственной причины тайм-аута. Конфигурация сервисов не менялась.

В пересозданном backend-admin выполнено:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_agents.py chatballs/integrations/action_catalog/test_native_settings.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/ai/test_agent_cards.py chatballs/ai/test_test_chat.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

50 passed, 1 failed, 38 warnings (685.06 s). Все новые проверки native-агентов,
настроек, inventory и переводов прошли. Единственный сбой — старое ожидание
`assertNotIn("номер", provider.sent())`: слово присутствует в штатной инструкции
о номере запуска, независимо от маскируемого значения. Тестовое значение и
ожидание заменены уникальным маркером без изменения продуктового промпта.
Адресный повтор этой проверки и существующих проверок справочника агентов:

```sh
python -m pytest chatballs/ai/test_test_chat.py::TestChatTests::test_escaped_values_are_masked_and_restored_without_escaping_artifacts chatballs/ai/test_knowledge_list.py::AgentDirectoryTests --reuse-db -q --tb=short
```

3 passed, 4 warnings (127.82 s). Ruff исправленного теста и повторный
`git diff --check` также прошли.

Ruff, AST и `git diff --check` прошли до изменения тестового маркера;
33 Python-файла этой части не превышают 164 строк. Новый браузерный результат
не заявляется, коммит и сдача этого блока не выполнены.

## Навыки и восстановление среды: 05.11.2026

Добавлены 13 действий навыков: конфигурация, назначения агентам, проверка,
предпросмотр и основа заказов. Штатные сервисы сохраняют requestId, проверку
ревизии и изоляцию шаблонов. Inventory содержит 231 API-запись.

После тайм-аутов изучен реальный процесс Vite: главный поток и четыре потока
libuv ожидали `p9_client_rpc`. Прямой backend отвечал, прокси Vite задерживался.
В dev-конфигурации frontend/web-chat интервал polling увеличен с 300 до 1000 мс,
а пул libuv — до 16 потоков. Это уменьшает нагрузку обхода Windows bind mount
и конкуренцию файловых операций с DNS. Сервисы, данные и порты сохранены.
После `start_environment` readiness через frontend вернул 200 за 348 мс,
`database=true`, `redis=true`. Холодная загрузка модулей интерфейса оставалась
медленной; после неё штатные запросы каталога и списка сценариев вернули 200.

В backend-admin после подтверждённой готовности выполнено:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_skills.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/ai/test_skills_api.py chatballs/ai/test_skills_templates_api.py chatballs/ai/test_skills_access.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

26 passed, 17 warnings (484.07 s). Предыдущий прерванный пересозданием контейнера
процесс не считается успешной проверкой. Обе сборки прошли:
`docker compose exec -T frontend npm run build` (Vite 4m56s, предупреждение о
крупных chunks) и `docker compose exec -T web-chat npm run build` (Vite 26.93s).

В браузере проверены формы настроек, агента и навыка в общем редакторе.
У агента справочник языка показывает четыре локализованных варианта.
У навыка доступны вложенная конфигурация, массив шаблонов и поля шаблона.
Скриншоты `settings-editor.png`, `agent-editor.png`, `skill-editor.png` просмотрены.
Несохранённый черновик закрыт через «Не сохранять»; действия изменения данных
из редактора не запускались. После загрузки страницы ошибок консоли не было.
Эти проверки не подтверждают готовность ещё не подключённых доменов.

После исправления redaction и повторного `start_environment`:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_agents.py chatballs/ai/test_diagnostic_redaction.py chatballs/integrations/execution/test_result_payloads.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

21 passed, 2 warnings (345.92 s). Проверены числовые `max_tokens` и
`max_completion_tokens`, удаление сохранённого секрета и неизвестных
password/Bearer-значений из диагностики до записи receipt и показа журнала.
Общий предикат секретных ключей используется и в диагностике, и в журнале.
В браузере подтверждены разные подписи проверки/предпросмотра нового и
существующего навыка; второй черновик также закрыт без сохранения.
AST и Ruff проверены для 45 Python-файлов блока, максимум — 274 строки.

Пробел произвольных примеров навыков устранён и проверен вместе с
[действиями порталов и общим контролом значений](portals-structured.md).

## Дальнейшая проверка

[Сервисные подключения и скачивание файла знаний](services-files.md) проверены
отдельным адресным прогоном и в штатном браузере.

[Транспортные/AI-подключения и изображения виджета](connections.md) проверены
следующим адресным прогоном из 53 тестов и в общем редакторе.

Управление сценариями, финальный inventory и проверки: [результат](scenarios.md).
Архитектурная приёмка и сдача фиксируются сервисными ответами Skaro.
Промежуточный журнал не заменяет `submit_result` и не объявляет planned-архитектуру current.

Разрешённое владельцем слияние с main и адресная повторная проверка:
[результат слияния](main-merge.md).
