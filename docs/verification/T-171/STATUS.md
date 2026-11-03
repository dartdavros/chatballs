# Проверка T-171 — 03.11.2026

Реализация и адресные проверки выполнены. Решение о приёмке и публикации
определяет ответ Skaro на submit_result; этот файл сам по себе не подтверждает вливание.

Оба baseline лично приняты владельцем 22.10.2026 (SPEC-0037 R-28).
Архитектурный пакет T-171 применён Skaro, revision 8. Повторная приёмка
тех же макетов/пакета не запрашивалась. .skaro вручную не редактировалась.

## Штатный контур

start_environment подтвердил готовность frontend/backend, PostgreSQL и Redis.
Запущены backend-admin, worker и worker-events. Frontend проксирует API только
в backend-app этой задачи (VITE_DEV_API_TARGET=http://backend-app:8000).

- frontend: http://localhost:20004
- API: http://localhost:20002
- platform: http://localhost:20003
- web-chat: http://localhost:20005

Уже установленный демо-набор: INSTALLED, organization 1, 931 records.
Сервисных подключений 0. Seed, reset, смена паролей/TOTP/ролей/доступов,
временные HTTP-серверы и сетевые заглушки не использовались.
Прежняя блокировка отсутствующим Docker Engine устранена: штатный запуск повторён.

## Автоматические проверки

Все команды выполнены в task environment; backend использует --reuse-db.
Это адресный набор интеграционного исполнения, а не полный прогон проекта.

| Проверка | Результат | Лог |
| --- | --- | --- |
| execution + scenarios/test_validation.py + scenarios/test_values.py + i18n CatalogTests | 98 passed, 665.46 s | affected-current.log |
| test_composite_limits + test_nested_authority + test_composition + test_wait_clock + CatalogTests после уточнений бюджета | 21 passed, 139.15 s | limits-current.log |
| test_composite_retention + test_retention + test_api после сохранения безопасных статусов | 12 passed, 193.70 s | retention-current.log |
| 5 затронутых frontend-файлов тестов редактора, значений, ленты и переводов | 12 passed | frontend-tests.log |
| npm run build во frontend: tsc + Vite | exit 0 | frontend-build.log |
| manage.py check | no issues | backend-check.log |
| makemigrations --check --dry-run | no changes detected | migration-check.log |
| Ruff затронутых execution/events/scenarios/adapter модулей | all checks passed | вывод инструмента |
| git diff --check, размеры изменённых Python/TS/TSX | пройдены; превышений 300 / 180 строк React нет | вывод инструмента |

Команды:

```sh
docker compose exec -T backend-admin pytest chatballs/integrations/execution chatballs/integrations/scenarios/test_validation.py chatballs/integrations/scenarios/test_values.py chatballs/i18n/tests.py::CatalogTests --reuse-db -p no:cacheprovider -x -q --tb=short
docker compose exec -T backend-admin pytest chatballs/integrations/execution/test_composite_limits.py chatballs/integrations/execution/test_nested_authority.py chatballs/integrations/execution/test_composition.py chatballs/integrations/execution/test_wait_clock.py chatballs/i18n/tests.py::CatalogTests --reuse-db -p no:cacheprovider -x -q --tb=short
docker compose exec -T backend-admin pytest chatballs/integrations/execution/test_composite_retention.py chatballs/integrations/execution/test_retention.py chatballs/integrations/execution/test_api.py --reuse-db -p no:cacheprovider -x -q --tb=short
docker compose exec -T frontend npm test -- src/features/integrations/scenarios/model.test.ts src/features/integrations/scenarios/controlModel.test.tsx src/features/integrations/scenarios/aggregateOutput.test.ts src/features/integrations/runs/feed.test.ts src/i18n/catalog.test.ts
docker compose exec -T frontend npm run build
docker compose exec -T backend-admin python manage.py check
docker compose exec -T backend-admin python manage.py makemigrations --check --dry-run
```

98/21/12 пересекаются; это не сумма уникальных тестов. Последующие адресные
прогоны проверили последние изменения, а не подменены старым успешным логом.
Предупреждения: существующая Django CheckConstraint deprecation и отсутствие
staticfiles в dev-тестах; Vite предупреждает о размере chunks. Сборка успешна.

Проверены snapshot главного/вложенного определения, sequence/if/foreach/parallel/
call/wait/try, фактические типы и зависимости, отдельные пути, join/частичный
результат, падение после commit, stale fence, отсутствие повторов, nested grants
и циклы. Проверены ранние/повторные/out-of-order/чужие callbacks, подпись,
receipt+outbox до ACK с rollback, ответ только того же диалога, внутренние факты,
deadline/решение, DST, отмена/отзыв и лимиты. Истёкший долгий результат остаётся
unknown. Превышение бюджета не создаёт ребёнка без начального checkpoint.
Очистка удаляет values, сохраняя безопасные статусы до срока журнала.

## Browser в штатном приложении

Использован task-local Playwright. Администратор Елена Кузнецова создал через
редактор сценарий «Проверка составных ожиданий»: решение инициатора, затем две
параллельные ветви с ожиданием по минуте. Сценарий сохранён и явно включён.
Запуск из существующего диалога №31 создан реальным API (201), дошёл через
worker-events до confirmation, показал сохранённый текст и срок; после решения
выполнил обе ветви и завершился успешно. Сроки не переписывались ради проверки.

Run: 7e074568-fb34-4d1e-aef9-93b40334ff28, №1.
Сохранённые deadline двух ветвей: 03.11.2026 09:46:08/09 UTC;
finished_at: 03.11.2026 09:46:10.618455 UTC.

Проверены формы if/foreach/call/try, parallel с вложенными шагами и все варианты
wait: ответ, длительность, местное время, точная дата/время, событие, решение.
Проверен выход с несохранёнными изменениями; черновик отброшен через штатный UI.
Общий журнал и подробности проверены при 1440/1024, мобильная лента — при 390.
Тёмная тема взята из существующего профиля сотрудника Светланы Петровой;
светлая — из существующего профиля администратора. Просмотр сотрудником не
выдал ему управляющие права. PNG в этой папке показывают фактическое приложение.

Реальный внешний сервис не проверен. Независимые independent/ledger адаптеры
использованы только в автоматических контрактных тестах: новый составной
сценарий обращается к двум разным descriptor-пакетам без правки runner/UI.
Они не зарегистрированы в продукте и не являются сетевым fake backend.
Подписки/синхронизация, ИИ и полный каталог native actions следующих задач не
объявляются завершёнными вместе с T-171. Рабочий день без штатного календаря
даёт объяснимую недоступность вместо выдуманной пятидневки, как принято в revision 8.

В первой браузерной сессии чат давал существующие 409 email/options для закрытого
непочтового диалога и предупреждения о повторном ключе строки диалога. Эти
соседние функции не изменялись и не выдаются за проверенные исправления T-171.
После обновления страницы редактор и административный журнал проверены без
ошибок консоли. В dev-контуре наблюдалась долгая загрузка API; результаты
дожидались фактических ответов, неполная загрузка не считалась успехом.
