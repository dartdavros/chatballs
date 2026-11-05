# T-176 — каталог установки и полный inventory

Дата: 2026-11-05. Работа продолжается; этот журнал не является приёмкой задачи.
Личная приёмка обоих baseline зафиксирована в SPEC-0037 R-28 от 22.10.2026.
Пакет архитектуры `skaro-c4-7b23c98f-f50c-4ba8-b1a6-ea56586845df`
принят владельцем и применён Skaro, revision 24. После применения
`get_c4_context`: problems=[], projectProblems=[]. Planned не переведены в current.

## Реализация

Общий исполняемый реестр: 301 действие, из них 275 tenant и 26 глобальных.
Добавлены 12 instance, 10 personal, 1 platform, 3 bootstrap. По умолчанию
реестр/редактор/runner разрешают только tenant; `authority=None` предназначен
для серверной инвентаризации. Право администратора установки у делегата
не расширяет tenant-сценарий. Domain services общие с исходными HTTP API.

Полная базовая опись: 367 входов, 304 product-связи, 42 protocol, 16 credential
protocol, 4 health, 1 transport. Product: 278 tenant, 12 instance, 10 personal,
1 platform, 3 bootstrap. Несколько входов могут ссылаться на одно действие.
HTTP resolver обходится полностью для app/platform, плюс socket inventory.
Неизменённые framework HEAD/OPTIONS выводятся проверяемым правилом; собственные
реализации не исключаются автоматически. Каждой записи задан code evidence.
С учётом 408 framework aliases: 775 записей, `problems() == []`; число
transport-записей становится 409. Это измерено manage.py shell в текущем контуре.

Разделены instance settings/email/tools, storage, updates, personal
profile/language/files/sessions, organization creation, platform provisioning
и setup. Закрытые схемы и подписи ru/en описывают фактические поля.
Сохранены domain validation, аудит и прежние процедуры. Добавлены повторная
проверка активного principal/токена/сессии и защита от перезаписи конкурентной
конфигурации после S3 probe. HTTP к себе, APIView dispatch и универсального
SQL/CRUD нет. Обновление установки и перенос хранения реально не запускались.

## Исполненные проверки

Окружение `skaro-chatballs-t-176` запускается только через Skaro:
PostgreSQL, Redis, backend-app/platform/admin, frontend, web-chat,
worker/worker-events. Frontend: `http://localhost:20004`, app API `:20002`,
platform `:20003`. `VITE_DEV_API_TARGET=http://backend-app:8000`.
Readiness через frontend: HTTP 200, database=true, redis=true.
Backend-admin добавлен штатным configure_environment для адресных тестов.
Seed, reset, временные HTTP-серверы, fake backend и изменение доступов не применялись.

Сборка: `docker compose exec -T frontend npm run build`, tsc + Vite,
4665 modules, Vite 1m47s, exit 0. Предупреждение о крупных chunks.
Все изменённые Python: `ruff check`, exit 0. `git diff --check`, exit 0.
Изменённых Python/JSON/Markdown файлов длиннее 300 строк нет.

Проверки ниже выполнялись через `docker compose exec -T backend-admin`.
Полный прогон проекта не запускался.

```sh
python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_auth_boundary.py chatballs/integrations/action_catalog/test_http_coverage.py chatballs/integrations/action_catalog/test_global_authority.py chatballs/integrations/action_catalog/test_native_installation.py chatballs/identity/test_organization_creation.py chatballs/identity/tests.py::AuthEndpointTests::test_profile_update_changes_current_user_identity chatballs/identity/tests.py::AuthEndpointTests::test_profile_appearance_saves_theme_and_accent chatballs/identity/tests.py::AuthEndpointTests::test_profile_language_saves_personal_choice chatballs/platform/tests/test_platform_auth.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short -x
```

33 passed, 18 warnings, 83.44s. Проверены полное точное покрытие API,
отдельная классификация auth, пользовательские HEAD/OPTIONS, новые префиксы,
ru/en схемы всех областей; недоступность глобальных действий tenant resolver,
сохранение SMTP секрета, redaction, отзыв instance-права, конфликт S3 probe,
собственные/чужие/отозванные сессии, деактивация пользователя, platform replay
и отзыв токена, закрытый bootstrap, прежние профиль и создание организации.

```sh
python -m pytest chatballs/identity/test_setup.py::SetupWizardTests::test_complete_creates_organization_owner_and_logs_in chatballs/identity/test_setup.py::SetupWizardTests::test_setup_closes_after_first_owner chatballs/identity/test_setup.py::SetupWizardTests::test_validation_errors_name_the_fields chatballs/identity/test_setup.py::SetupWizardTests::test_weak_password_is_rejected_before_anything_is_written chatballs/integrations/adapters/test_schema_registry.py chatballs/identity/test_instance_address.py::InstanceSettingsAccessTests chatballs/updates/tests.py::InstallRequestTests --reuse-db -q --tb=short -x
```

30 passed, 14 warnings, 40.87s. Проверены исходный HTTP-мастер/вход владельца,
ошибки полей/слабый пароль, граница manager-read/instance-admin-write,
прежняя процедура updater, независимый probe adapter, схемы/обработчики/
справочники/расширения/версии контролов. Probe существует только в unit-тестах;
это не подключение настоящего внешнего сервиса.

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_composition.py chatballs/integrations/execution/test_native_ai_scenario.py chatballs/integrations/execution/test_native_automation.py --reuse-db -q --tb=short -x
```

5 passed, 1 warning, 101.62s после окончательного start_environment.
Общий исполнитель сохраняет связывание service/native результатов, внутренние
доменные эффекты, явного делегата ИИ/автоматики и повторную проверку grant.
Независимый адаптер здесь тестовый: реальные внешние эффекты не заявляются.

Предупреждения тестов: старый Django CheckConstraint и отсутствующий
staticfiles в тестовом контейнере. Ранний прогон остановлен на повторных
проверках coverage после 26 passed; он не считается завершённым. Дублирующий
обход по старым префиксам удалён: единая точная проверка охватывает все входы.
Проверка evidence проверяет каждый уникальный путь один раз за обход.

Ранее в этой задаче прошли 40 адресных проверок instance/tools/storage/update
и i18n после исправления тестового host с localhost на 127.0.0.1; три других
новых проверки прошли до этого. Эти результаты не прибавляются повторно к
итоговым 33/30 и не объявляются полным прогоном.

## Браузер и реальные ограничения

Task-local Playwright, существующий demo ADMIN. Наличие активного аккаунта
и membership проверено read-only в копии БД; is_instance_admin=false.
Профиль, avatar API и собственные сессии: HTTP 200. Текущая сессия показана,
компоновка [профиля](profile.png) просмотрена, горизонтального overflow нет.
Пароли, TOTP, сессии, роли и доступы не изменялись.

Штатный каталог редактора: HTTP 200, 276 схем (275 tenant-действий плюс
schema-only entity_link.create). Ни одного ключа `chatballs:instance.*`,
`platform.*`, `profile.*`, `setup.*`, `organizations.*` не получено.
Диалог выбора шага осмотрен; globals отсутствуют, существующие способы
запуска/блоки сохранены. Несохранённый черновик закрыт через «Не сохранять».
Instance settings/storage GET под этим аккаунтом вернули штатный 403;
изменяющие административные запросы не отправлялись.

В исходном чате наблюдались 409 email/options и React duplicate key 31;
409 для этого диалога также зафиксирован в отчёте T-173. Во время autoreload
было переподключение WebSocket. Чистая проверка всего приложения не заявляется.
Профиль и каталог после переподключения отвечали штатно.
После окончательного start_environment снова подтверждены readiness БД/Redis,
276 tenant-схем, 0 глобальных ключей, sessions HTTP 200; консоль на текущем
экране профиля: 0 errors, 1 warning. Это не отменяет ошибки исходного чата выше.

Read-only проверка ServiceConnectionSettings: 0. В текущем контуре отсутствует
реальный сервисный доступ. Поэтому полный путь «подключение → готовый/свой
сценарий → сотрудник/ИИ/автоматический инициатор → внутренние/внешние шаги →
журнал/восстановление» здесь ещё не подтверждён. Реальная внешняя запись,
файлы/OAuth, callback/сверка после эффекта, синхронизация и наполненные состояния
UI не выдаются за пройденные. Unit-контракты не заменяют эти проверки.

05.11.2026 владелец ответил на защищённый запрос реального сервиса и доступа:
«пропусти», «я сам проверю потом». Внешние проверки переданы владельцу по его
прямому указанию; агент не запрашивает доступ повторно и не выполняет их.
Это решение о пропуске проверки сейчас, а не доказательство её прохождения
или личная приёмка всех оставшихся критериев. Ограничения 5–8 и полноты R-1–R-31
сохраняются в отчёте; общая готовность функции не объявляется.

## Соответствие критериям на этой стадии

1. Gate обоих baseline подтверждён принятой SPEC-0037 R-28.
2–4. Реализация и адресные проверки каталога/границ выполнены; окончательный
вердикт принадлежит submit_result, а не этому тексту.
5. Открыт: отсутствует реальное сервисное подключение и полный смешанный путь.
6. Registry/схемы/расширения проверены контрактно; реальный независимый адаптер
и отсутствовавший сценарий в штатном контуре ещё не подтверждены.
7. Предыдущие доказательства T-168–T-175 сохраняются в соответствующих журналах.
Новая проверка глобальных прав/сессий/секретов/конкурентного probe выполнена;
общая реальная интеграционная проверка остаётся открытой.
8. Справка и контракт обновлены; сборка и адресные проверки выполнены в указанном
объёме. Недостающий полный браузерный путь остаётся открытым.
9. Для реализации e3024d72 сохранён exact C4 review revision 24; после этой
записи решения владельца перед submit_result review повторяется. Квитанция
Skaro определяет актуальный changeHash. Полная готовность R-1–R-31, этапа
и публикация здесь не заявляются.

Справка: [ru](../../native-scenario-actions.ru.md),
[en](../../native-scenario-actions.en.md),
[контракт/восстановление](../../native-global-actions.md).
Полная сверка требований: [R-1–R-31](requirements.md).
