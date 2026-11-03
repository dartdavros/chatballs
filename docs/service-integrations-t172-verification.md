# T-172: проверка автоматизации и обмена

Дата: 03.11.2026. Это отчёт о выполненных проверках, не приёмка всех критериев
и не подтверждение публикации. Оба baseline лично приняты владельцем ранее
(22.10.2026, SPEC-0037 R-28); принятый пакет C4 revision 10 прочитан без problems.

## Штатное окружение

Skaro запустил собственное окружение skaro-chatballs-t-172 на исходниках задачи,
с копией данных основной установки: frontend http://localhost:20004,
backend-app http://localhost:20002, platform http://localhost:20003,
web-chat http://localhost:20005. PostgreSQL и Redis healthy; readiness проверяет
реальные БД/кеш. backend-admin доступен внутри Compose для тестов.
Запуск включает backend-app/backend-platform/backend-admin, worker,
два worker-events, frontend/web-chat, PostgreSQL/Redis; миграции выполняет init.
После последней схемы delivery lease выполнен start_environment и получен ready.
Ручного compose up, seed, fake backend, временных HTTP-серверов, изменения
паролей/TOTP/ролей/ActionGrant или служб других задач не выполнялось.

## Воспроизводимые проверки

Команды ниже запускаются из корня checkout с переменными штатного окружения.
В PowerShell установленный docker.exe можно вызывать полным путём из Docker Desktop.

```text
docker compose exec -T frontend npm run build --workspace @chatballs/internal-ui
```

Прошла сборка TypeScript + Vite, 4634 modules; штатное предупреждение о chunks
больше 500 kB не является ошибкой сборки.

```text
docker compose exec -T backend-admin python -m pytest chatballs/integrations/automation_events chatballs/integrations/scenarios/test_synchronization_plan.py chatballs/integrations/scenarios/test_synchronization_runtime.py chatballs/integrations/adapters/test_reference_urls.py chatballs/i18n/tests.py --reuse-db -p no:cacheprovider -q --tb=short
```

47 passed, 1 skipped. Для первого итогового запуска после новой миграции 0028
добавлен --create-db: пересоздана только отдельная тестовая БД после изменения
схемы/прерванного окружением предыдущего теста. Обычный повтор — с --reuse-db.
Skipped — существующая проверка frontend-каталога в backend-контейнере, где
frontend не смонтирован; TypeScript и frontend-тесты выполнены отдельно.
Проверены durable receipt/audience/outbox и rollback до ACK, независимый fan-out
и сбой после частичного commit, устойчивость к ревизии, отзыв делегирования,
возобновление после паузы, cursor rollback/fence, scoped API/idempotency/rotation,
DST fold/gap, skip/once и slot dedup, направленные mappings, отсутствие
автоматического слияния по email, ручной конфликт/устаревшее решение/отмена,
удаление/снятие связи, подавление обратного изменения, поиск без автоматического
выбора/замена/снятие, RLS чужой связи, retention с nullable Run и восстановление
native receipt после падения отдельного runner commit. Ссылка карточки не
раскрывает секретный webhook path.

Независимый exchange_contract_testing — только автоматический контрактный тест
в отдельной тестовой БД. Он не установлен в продукте, не создаёт HTTP-сервис
и не служит доказательством реальной внешней интеграции.

```text
docker compose exec -T backend-admin python -m pytest chatballs/conversations/rules/test_receipt_confirmation.py chatballs/conversations/rules/test_reply_reminder.py chatballs/conversations/rules/test_email_reminder.py chatballs/conversations/rules/test_assignment_return.py --reuse-db -p no:cacheprovider -q --tb=short
```

21 passed: четыре прежних вида правил. Отдельно ранее прошли затронутые
MainTransitionRuleTests и scheduler-совместимость; существующие обработчики
не перерегистрируются и не вызываются из интеграционного fan-out.

```text
docker compose exec -T frontend npm run test --workspace @chatballs/internal-ui -- src/features/integrations/runs/feed.test.ts src/features/integrations/scenarios/model.test.ts src/features/integrations/scenarios/controlModel.test.tsx src/features/integrations/scenarios/aggregateOutput.test.ts src/features/integrations/services/model.test.tsx
```

5 файлов, 15 тестов прошли. Ruff прошёл для всех изменённых/новых Python-файлов.
makemigrations integrations tenancy --check --dry-run: No changes detected.
Проверка длины всех затронутых Python/TS/TSX: файлов длиннее 300 строк нет;
новые UI-компоненты разделяют model/hooks/subviews и используют ru/en словари.
Полный backend/frontend набор не запускался.

## Browser: реальный API и журнал

Task-local Playwright, существующая демо-учётная запись администратора из
документации проекта; наличие membership проверено до входа. В UI создан
«Проверка автоматизации T-172»: внешний API, область организации, явное
разрешение запуска без сотрудника, один минутный шаг ожидания. Права аккаунта
и ActionGrant не изменялись. Сохранение/включение прошло штатным POST API (201).
Одноразовый ключ использован только в памяти проверки, в отчёт/скриншоты не попал.

Два реальных POST на scenario-triggers с одинаковым Idempotency-Key:
202, один Run a8dcdd36-1e65-4be4-bed0-1c4f5186c0d7,
сначала duplicate=false, затем duplicate=true. worker-events выполнил ожидание;
Run completed, createdAt 17:09:48 UTC, finishedAt 17:10:52 UTC.
Открыты список, журнал и карточка: «Успешно», шаг «Подождать» завершён.
На 1280×720 и 390×844 scrollWidth равен ширине viewport, переполнения нет.
В момент проверки и сохранения скриншотов: 0 console errors; существующее предупреждение библиотеки
не объявлено ошибкой функции. Во время предыдущих reload были таймауты пула/
WebSocket; после окончательного start_environment эти сессии не использовались
как доказательство успеха.

Скриншоты: [desktop](verification/t172-api-run.png),
[mobile](verification/t172-api-run-mobile.png).

## Открытые проверки и ограничения

Прямое read-only чтение копии рабочей БД: ServiceConnectionSettings — пусто.
Нет реального подключения/endpoint/доступа внешнего сервиса. Поэтому реальный
webhook/cursor и внешняя запись/удаление не проверены. Нельзя объявить пройденными
заполненные UI состояний связанных записей, поиска/замены и ручного конфликта,
а также результаты обмена в карточке реального подключения. Unit/контрактные
тесты этих механизмов не заменяют browser/внешнюю проверку.

Bitrix24 сейчас предоставляет read binding и поиск. Исходящий обмен, требующий
условной записи, блокируется; обычный crm.*.update не объявлен CAS. Отсутствие
возможности адаптера не обходится безусловной записью. Не создаётся CRM-мастер-база,
не придумываются публичное удаление контакта/переоткрытие закрытого диалога.
Общий native-каталог и ИИ следующих задач не объявляются готовыми.

Критерии 2, 7 и 8 остаются открытыми в части указанных реальных внешних и browser
проверок. Итог задачи/этапа и публикация не подтверждены. Уточнение путей модулей принято владельцем и применено Skaro:
пакет skaro-c4-20e0a482-b344-46de-9e6b-3aee8129fdb1, revision 11.
get_c4_context после применения: problems=[], projectProblems=[].
Это не заменяет внешние проверки; C4 review относится к окончательному changeHash.

Дополнительные проверки общего runner:

```text
docker compose exec -T backend-admin python -m pytest chatballs/integrations/execution/test_composition.py chatballs/integrations/execution/test_nested_authority.py chatballs/integrations/execution/test_execution.py --reuse-db -p no:cacheprovider -q --tb=short
```

18 passed. Финальный manage.py check: System check identified no issues.

Адресная проверка принятого контракта таблиц статусов:

```text
docker compose exec -T backend-admin python -m pytest chatballs/integrations/scenarios/test_synchronization_plan.py chatballs/integrations/scenarios/test_synchronization.py --reuse-db -p no:cacheprovider -q --tb=short
```

8 passed. Выбор «не менять» (null в таблице соответствия) сохраняет получателя.
