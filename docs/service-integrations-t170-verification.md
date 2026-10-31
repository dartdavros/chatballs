# T-170: проверка исполнения — 30.10.2026

Задача не объявлена завершённой. Код общего одношагового пути, ручного запуска,
журнала и очистки подготовлен; внешние и часть визуальных проверок остаются
открытыми. Документ фиксирует выполненные проверки, а не приёмку всех критериев.
Основной пакет C4 и уточнение об отложенных источниках применены Skaro
(revision 7, пакет skaro-c4-cb21ce43-03f1-4334-97c7-7fc2f6e0a089).
get_c4_context после применения: problems=[]. Planned не становится current
от коммита или этого отчёта.
Архитектурная проверка и поэлементные вердикты критериев сохраняются в Skaro
по окончательному changeHash; этот отчёт не заменяет review_c4/submit_result.

## Среда

Штатный Skaro Compose `skaro-chatballs-t-170`, текущие адреса:
frontend http://localhost:20004, API http://localhost:20002,
platform http://localhost:20003, web-chat http://localhost:20005.
PostgreSQL и Redis healthy; ready через frontend:
`{"status":"ok","checks":{"database":true,"redis":true}}`.
`VITE_DEV_API_TARGET=http://backend-app:8000`.
Backend-admin добавлен в документированную launch-команду через Skaro,
остальные сервисы и выделенные порты сохранены.

Docker Desktop был остановлен. После явного указания владельца запущен;
Engine 29.8.1, окружение поднято через start_environment. Замены контура нет.
Демо-набор организации 1 уже установлен: INSTALLED, 931 запись.
Использован существующий ADMIN из манифеста, seed/смена пароля/ролей не выполнялись.
ServiceConnectionSettings организации 1: 0. Владелец разрешил продолжать без
внешнего доступа; это не снимает непроверенные критерии.

## Исполняемые проверки

Команды выполнялись в этом Compose:

```text
docker compose exec -T frontend npm run build --workspace @chatballs/internal-ui
docker compose exec -T backend-admin pytest chatballs/integrations/execution --reuse-db -p no:cacheprovider -q --tb=short
docker compose exec -T backend-admin pytest chatballs/integrations/execution/test_api.py --reuse-db -p no:cacheprovider -q --tb=short
docker compose exec -T backend-admin pytest chatballs/integrations/execution/test_deferred_sources.py chatballs/integrations/execution/test_execution.py chatballs/integrations/execution/test_access_recovery.py chatballs/integrations/execution/test_api.py --reuse-db -p no:cacheprovider -q --tb=short
docker compose exec -T backend-admin pytest chatballs/integrations/execution/test_direct.py chatballs/integrations/execution/test_worker.py --reuse-db -p no:cacheprovider -q --tb=short
docker compose exec -T backend-admin pytest chatballs/integrations/execution/test_worker.py --reuse-db -p no:cacheprovider -q --tb=short
docker compose exec -T frontend npm run test --workspace @chatballs/internal-ui -- src/features/integrations/runs/feed.test.ts src/features/conversations/feed.test.ts src/shared/Pagination.test.tsx src/features/integrations/scenarios/controlModel.test.ts
docker compose exec -T backend-admin pytest chatballs/integrations/execution/test_api.py chatballs/i18n/tests.py --reuse-db -p no:cacheprovider -q --tb=short
docker compose exec -T backend-admin python manage.py check
docker compose exec -T backend-admin python manage.py makemigrations --check --dry-run
docker compose exec -T backend-admin ruff check chatballs/integrations/execution chatballs/integrations/scenario_state chatballs/integrations/adapters/files.py chatballs/integrations/adapters/http.py chatballs/i18n/messages/runs_ru.py chatballs/i18n/messages/runs_en.py
git diff --check
```

Итоги: сборка exit 0 (4625 модулей, 1m41s; предупреждение о chunks >500 kB);
execution — 34 passed. После уточнения доступности остановленного подключения
повторены только затронутые API-тесты: 6 passed, Ruff passed. Frontend —
14 passed в четырёх адресных файлах. Каталог i18n вместе с прежней версией
API-тестов — 16 passed, 1 штатный skipped. Django check без ошибок,
makemigrations — No changes detected, diff --check без дефектов whitespace.
Полный набор проекта не запускался.

После решения владельца об отложенных источниках повторно собран backend через
start_environment. Проверка test_deferred_sources + test_execution +
test_access_recovery + test_api — 24 passed, 8 warnings за 145.91 s.
Django check и Ruff повторены без ошибок. Проверено, что отрицательные условия,
группа any и object.get не обходят недоступность источника; каталог запрещает
такой запуск, Run/outbox не создаются, старый snapshot не отправляет эффект.
Литеральные constant payload не принимаются за ссылки. Новый source_support.py
содержит 44 строки, файл тестов — 77; обязанности разделены, новый UI не добавлен.

После применения C4 revision 7 добавлены только адресные тесты прямого запуска
и ограничений воркера. Первый прогон — 5 passed, 1 failed: тест использовал
несуществующее поле available_at вместо next_attempt_at. Исправлен только тест,
потоки завершаются до восстановления подменённого семафора. После повторного
start_environment затронутый test_worker.py — 2 passed, 1 warning за 30.23 s;
test_direct.py — 4 passed в первом прогоне. Ruff и diff --check прошли.
Проверены настоящий пул из двух потоков, возврат в dispatcher при занятых слотах,
сохранённое будущее outbox-задание, независимость другого подключения от cooldown,
остановка постоянной ошибки, прямой вызов EMPLOYEE с точным разрешением,
dedup неизменяемого snapshot, отзыв разрешения и понятный version mismatch.
Эти данные создаются только в изолированной тестовой PostgreSQL-базе.
Новых записей/разрешений в рабочую копию данных не добавлялось.
Новые файлы тестов — 85 и 103 строки. Frontend не изменялся; повтор его сборки
и browser-проверок после добавления backend-тестов не требовался.

Проверены реальные конкурирующие PostgreSQL-сессии для dedup/lease/RLS,
stale fence, сохранение effect key, rollback Run/Step/outbox, потеря ответа
и падение после send marker, NONE/idempotency/reconcile/safe-read, отзыв прав,
пауза/отключение/отмена, точное/истёкшее подтверждение, намеренный повтор.
Файловые тесты используют настоящий временный каталог теста: активный
потребитель защищает файл, independent_owner сохраняет его, ошибка storage
оставляет повторяемое удаление. Проверены 7/30, активные ожидания, 24-часовая
задержка и её отмена, минимальный dedup tombstone без payload/actor/context.
Это unit/DB проверки контракта, не демонстрационный backend и не внешний сервис.

Первоначальный дефект FOR UPDATE на nullable outer join исправлен;
повтор файловых тестов — 3 passed, затем они вошли в 34 passed.
Первоначальная ошибка ключа перевода остановила tsc; ключ добавлен, итоговая
сборка прошла. Фоновый polling больше не делает медленный ответ устаревшим
каждые 15 секунд; реальный журнал после исправления выходит из загрузки.

## Браузер в штатном приложении

Task-local Playwright, реальный backend, cookies существующего demo ADMIN.
Проверены загрузка/пустой журнал, поиск с «Ничего не найдено», меню периода,
возврат к пустому списку и ссылка в настройки хранения. Журнал при 1440×1000
и 1024×900 не переполняет страницу. Поле поиска восстановлено до 280 px,
селекты без выбранного ограничения не подсвечиваются как активные.

В настройках через UI изменено 7 → 3 дня: показано отдельное подтверждение,
API вернул stepDays=3, journalDays=30, version=2 и effectiveAt через 24 часа.
Затем через UI возвращено 7: API подтвердил stepDays=7, journalDays=30,
version=3, effectiveAt=null. Отложенное сокращение отменено; данные не удалялись.
Остальные настройки организации/профиля/доступов не менялись.

В настоящем диалоге проверено L5: подсказка отсутствия действий в карточке
контакта и отсутствие кнопки запуска в шапке; desktop overflow=false.
Мобильный чат проверяется при 390×844. Обнаружен конфликт существующих правил
width=60px !important и mobile width=0: исправлено правило схлопывания сайдбара.
Сборка выше предшествовала только этой CSS-правке; новая сборка исключительно
ради неё не запускалась по правилу владельца. После start_environment выполнена
browser-перепроверка: sidebarWidth=0, overflow=false, пустое состояние действий
в контексте доступно, кнопка запуска скрыта. Блок действий получил предусмотренные
baseline отступы 14×18 px и минимальную высоту 120 px для загрузки/пустого текста.

Под существующим EMPLOYEE с сохранённой DARK/#7c3aed (без правки профиля)
проверены пустое состояние действий при 1440 и мобильный чат 390×844:
theme=dark, overflow=false, sidebarWidth=0. После последнего start_environment
блок действий измерен: height=120, padding=14px 18px. Запрос общего журнала сотрудником
отклонён (HTTP 409). Настройки профиля, пароль и права не менялись.

Во время чата консоль также показывает 409 email/options для обычного WEB
диалога и повторяющиеся ключи числовых ID списка диалогов. Это не ключи нового
run-feed (`run:UUID`) и не исправлено этой задачей. Браузер целиком без ошибок
не заявляется. При development-перезагрузке был warning закрытого WebSocket;
рабочее подключение позднее установлено штатным сервером.

## Открыто для приёмки

- Нет реального подключения: не проверены внешний эффект и ответы справочников,
  manual preview/launch в штатном UI, filled/running/unknown/recovery/cancel
  карточки реального запуска и их realtime. Искусственные запуски в рабочую БД
  ради показа не создавались.
- Полная проверка обоих тем оформления и мобильных параметров/подробностей
  реального запуска не завершена. Проверка пустого журнала не заменяет её.
- Владелец 30.10.2026 явно выбрал отложить conversation.topic и метки контакта,
  внешние связи оставить T-172. Зависимые guards/bindings остаются недоступными;
  решение применено в C4 revision 7; соответствующий вопрос закрыт.
- Прямой вызов сотрудника требует существующего ActionGrant; управление его
  выдачей не имеет продуктового экрана в T-170, разрешения не создавались.
- Составные блоки/автоматизация/ИИ/native actions остаются следующими задачами.
  В этой задаче не проверена вся SPEC-0037 и не завершён весь этап.

Новые backend-модули меньше 300 строк, новые React-компоненты меньше 180;
composition/state/API/subviews разделены. Большие существующие i18n-каталоги
получили только импорт/подключение отдельного словаря runs.ru/en. Существующий
400-строчный layout.css изменён одной заменой приоритета ширины сайдбара;
новая ответственность или новый workflow в него не добавлены.
