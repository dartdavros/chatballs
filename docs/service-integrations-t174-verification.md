# T-174 — журнал адресной проверки

Промежуточный результат, задача не завершена. Полная приёмка и exact C4 review
ещё не выполнены. Наличие зарегистрированных действий не означает прохождения
всех критериев задачи или готовности этапа.

## Основа

Владелец разрешил перебазирование T-174 на опубликованный commit `44329988`
(T-172/T-173). Шесть прежних коммитов T-174 перенесены; сохранены автоматический
principal, ИИ-снимки/подтверждения, EntityLink и синхронизация. Для служебных
native-операций T-172 сохранён отдельный модуль `execution/native_system.py`;
каталог T-174 использует `execution/native.py` и зашифрованные квитанции.

Миграции `integrations/0030_merge_native_catalog` и
`tenancy/0078_merge_native_receipt_guards` соединяют ветви миграций без выдачи
новых прав и изменения существующих строк. Личная приёмка двух baseline
зафиксирована ранее в SPEC-0037 R-28 и документах T-167 основной копии проекта.

## Проверки после перебазирования

Штатное окружение `skaro-chatballs-t-174`, frontend `http://localhost:20016`,
API `http://localhost:20014`. Readiness через frontend proxy вернула HTTP 200
с `database=true`, `redis=true`. Backend, PostgreSQL, Redis и worker запускаются
Skaro; временные серверы, seed и изменение учётных данных не использовались.

Сборка интерфейса:

```sh
docker compose exec -T frontend npm --workspace @chatballs/internal-ui run build
```

Успех: TypeScript, Vite, 4643 модуля; известное предупреждение о размере чанков.
`python manage.py check` — без замечаний;
`python manage.py makemigrations --check --dry-run` — изменений нет.

14 проверок общего runtime после перебазирования прошли:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_comments.py chatballs/integrations/action_catalog/test_native_composition.py chatballs/integrations/execution/test_ai_scenarios.py::AgentScenarioTests::test_automatic_write_keeps_delegate_policy_after_agent_runtime_merge chatballs/integrations/execution/test_ai_scenarios.py::AgentScenarioTests::test_composite_snapshot_keeps_agent_policy_and_link_context chatballs/integrations/scenarios/test_synchronization_runtime.py::ExchangeRuntimeTests::test_common_runner_updates_and_echo_does_not_write_again chatballs/integrations/scenarios/test_synchronization_runtime.py::ExchangeRuntimeTests::test_reverse_updates_contact_without_merging_email_identity --reuse-db -q -x --tb=short
```

Проверены rollback/повтор локального эффекта, receipt/RLS, отзыв grant,
смешанные native/service шаги, автоматический write, ИИ-снимок и синхронизация
без повторной записи. Эти проверки сохраняют опубликованные механизмы;
они не доказывают полноту native-действий ИИ T-174.

## Действия качества и отчётов

API качества делегирует общему `conversations/quality/operations.py`.
Масштабы со смешанными строками/целыми/дробными значениями представлены
именованными полями; типы значений сохраняются. Запуск анализа возвращает
состояние очереди, не готовые выводы. Исправления сохраняют исходный результат,
проверяют ревизию, текущую область управления и доступность доказательств.

14 адресных проверок прошли:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_quality.py chatballs/integrations/action_catalog/test_native_reports.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

Исходные `conversations/quality/test_api.py` — 6 проверок прошли отдельным
первым запуском этой итерации; новые runner-тесты затем исправлены и пройдены.
При браузерной проверке обнаружена и исправлена порча новых ru-строк при
записи через PowerShell. Дополнительный тест подписей прошёл отдельно:
`test_catalog_coverage.py::NativeCoverageTests::test_executable_actions_have_translated_titles_and_named_inputs`
— 1 passed. Ruff по файлам текущей итерации исправил только порядок импортов;
замечаний не осталось. `docker compose build backend-app` прошёл.

В штатном редакторе проверены каталог, вложенные критерии/шкала и текстовое,
целое, дробное значение; форма периода/фильтров отчёта. При ширине 1280 документ
имеет scrollWidth=1280, панель — clientWidth=scrollWidth=480. Скриншоты Playwright:
`element-2026-11-04T11-56-18-659Z.png` и `element-2026-11-04T11-57-07-066Z.png`.
На этом экране ошибок консоли нет, новых layout/кнопок нет. Проверочный сценарий
не сохранялся. Общие финальные проверки журналов/всех действий остаются открытыми.

## Открытый объём

Каталог содержит 124 исполняемых действия исходной таблицы. Полное
соответствие исходным 125 продуктовым API-входам проверено problems()==[].
После включения SDK/socket входов каталог содержит 125 действий для 127
продуктовых входов из 155 классифицированных; см. feedback-verification ниже.
Текстовый ответ, запрос контакта, голосовое, вложение и расшифровка подключены;
см. service-integrations-t174-replies-verification.md. Почтовое продолжение,
общий I/O-протокол и файловые результаты также проверены.

Для grants ИИ владелец выбрал явного администратора-делегата native-разрешения;
C4-пакет skaro-c4-59265996-5fff-40b7-8b7c-996aa36b8e0f
лично принят владельцем и применён Skaro (revision 15); реализация
и проверки описаны в service-integrations-t174-ai-verification.md.
Полные типы отчёта, транспортная инвентаризация и их browser-проверки завершены:
см. service-integrations-t174-feedback-verification.md.

Полный набор тестов не запускался. Реальный внешний сервис не объявляется
проверенным: имеющиеся демонстрационные подключения не подтверждают доступ.

## Действия оценок клиентов

Шесть действий используют прежние настройки, защищённую карточку/выборку,
credential resolver и неизменяемый ответ клиента. Native-вызов resolver явно
передаёт ожидаемую организацию до чтения ресурса. Токен не выпускается грантом,
скрывается схемой в preview/journal; повтор голоса не создаёт второе событие.
Фильтры защищённого API вынесены в общий `ratings/queries.py` без изменения
его статусов или прав. Общая подготовка существующих Django-тестов вынесена
в `prepare_rating_transport`, производственные данные не создаются.

26 адресных проверок прошли:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_ratings.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/ratings/test_results.py chatballs/ratings/test_public.py chatballs/ratings/test_settings_defaults.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

Проверены current scope, межtenant/expiry/cancellation, повтор и изменение голоса,
redaction токена, единственность события, группировка по шкалам и отключение
опросов. Штатный build при `start_environment` выполнен; Ruff файлов этой
итерации проходит. Browser-проверка полей выполнена в штатном редакторе: ключ
имеет type=password, оценка выбирается общим enum-контролом с пятью переводами.
Скриншот: `element-2026-11-04T14-55-17-287Z.png`. Секрет не вводился, ответ
не отправлялся, сценарий не сохранялся. После добавления проверки canonical
conversation scope адресные runner-тесты оценок повторяются вместе со звонками.


## Звонки и область ресурса

Восемь действий звонков вызывают прежние lifecycle/credential services.
Общий `calls/operations.py` сохраняет доступ к диалогу и аудит для API/native.
Выдача staff/customer access credential остаётся двумя классифицированными
входами аутентификации. Native не возвращает выпущенные токены и ICE credentials;
приглашение/очередь доставки не объявляются установленным соединением.
Перед эффектом credential resolver сверяет tenant, side, subject, expiry;
UUID и credential сверяются с canonical conversation текущего Run. Runtime
пересекает область текущего grant с областью snapshot, а не расширяет её.

Штатная сборка `start_environment` и `manage.py check` пройдены. Через frontend
readiness возвращает HTTP 200 с database=true и redis=true. В редакторе проверены
восемь названий, параметры приглашения, enum аудио/видео. Документ: ширина и
scrollWidth 1280; панель: clientWidth=scrollWidth=480. Скриншот:
`element-2026-11-04T14-56-35-166Z.png`. В этой навигации ошибок консоли нет
(одно существующее предупреждение). Проверочный сценарий отброшен через
«Не сохранять», реальные звонки не инициировались. Проверка RTC/внешнего
транспорта этим не заменяется. Адресный прогон: 39 passed, 2 failed на неверных прописных строках кодов
событий в новых тестах. Исправлены только ожидания на SystemEvent-константы;
обе проверки затем пройдены (2 passed, 74.46 с). Поведение реализации не менялось.


Команда общего адресного прогона (578.85 с; не полный набор проекта):

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_calls.py chatballs/integrations/action_catalog/test_native_ratings.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_comments.py chatballs/integrations/action_catalog/test_native_composition.py chatballs/calls/tests/test_flow.py::CancelCallApiTests chatballs/calls/tests/test_flow.py::CustomerAccessApiTests chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

Повтор двух исправленных ожиданий:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_calls.py::NativeCallTests::test_customer_accept_and_end_keep_token_secret_and_original_terminal_state chatballs/integrations/action_catalog/test_native_calls.py::NativeCallTests::test_staff_actions_share_lifecycle_and_replay_does_not_create_another_call --reuse-db -q --tb=short
```

Ruff для всех 22 Python-файлов этого изменения проходит; файлов длиннее
300 строк нет. `git diff --check` проходит. Предупреждения тестов: существующие
Django 6.0 CheckConstraint и отсутствие каталога staticfiles в dev backend.


## Помощь сотруднику с ответом

Четыре действия используют прежние request/reject services; защищённые чтения
API/native вынесены в `ai/assistance_queries.py`. Очередь, history version,
проверки назначения и открытого диалога, исходный текст и автор отклонения
сохранены. Native operation key задаётся устойчивым effect_key шага. Действие
запроса возвращает состояние генерации, а не объявляет текст готовым.

Штатная сборка `start_environment` выполнена. Browser-проверка формы запроса,
четырёх названий и параметра альтернативной попытки выполнена. Документ
1280=scrollWidth, панель 480=scrollWidth; ошибок консоли нет, одно существующее
предупреждение. Скриншот `element-2026-11-04T15-16-06-997Z.png`. Проверочный
сценарий не сохранён; генерация и отправка через браузер не запускались.
Справка ru/en содержит пример запроса и чтения альтернатив.

Первый адресный прогон: 14 passed, 2 failed (215.57 с). Новый runtime-поведенческий
набор прошёл. Найдены пропущенный ru/en ключ номера варианта и старое ожидание
общего числа outbox-событий в исходном API-тесте: после T-172 там есть также
доменные факты. Ожидание уточнено до единственного ASSISTANCE_REQUESTED с
идентификатором созданного предложения; доменные события не подавляются.
После исправлений повторяются только две упавшие проверки.


Повтор после исправлений: 7 passed, 80.36 с. Штатная сборка текущих исходников
снова пройдена; Ruff проходит, новых/изменённых файлов длиннее 300 строк нет.

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_assistance.py chatballs/ai/test_assistance_api.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
docker compose exec -T backend-admin python -m pytest chatballs/ai/test_assistance_api.py::AssistanceApiTests::test_idempotency_alternative_and_rejection_preserve_each_source_and_author chatballs/integrations/action_catalog/test_catalog_coverage.py::NativeCoverageTests::test_executable_actions_have_translated_titles_and_named_inputs chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```


Файловые действия и I/O: [адресные доказательства](service-integrations-t174-files-verification.md).

Почтовое продолжение: [адресные доказательства](service-integrations-t174-email-verification.md).

Транспортные входы, полный feedback и текущая область сценария:
[адресные доказательства](service-integrations-t174-feedback-verification.md).
