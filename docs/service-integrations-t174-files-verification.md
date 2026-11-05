# T-174 — файлы и граница I/O

Промежуточная проверка, не финальная приёмка задачи.

## Реализация

Шесть действий используют исходные selectors/сервисы: аудио и вложение сообщения,
фото контакта, диагностический JSON и CSV/XLSX отчёта обслуживания. Общий
`media_queries.visible_message` используется также исходным HTTP-чтением аудио.
Проверяются tenant, видимость, canonical conversation/contact текущего Run и
первоначальные права отчёта/диагностики. Диагностический экспорт сохраняет
исходную очистку секретов; внутренние комментарии не становятся публичными.

`ServiceFile.integration` допускает null: native-файл не создаёт подключение.
Миграция 0031 применена штатным init. Путь использует серверную организацию,
квота/хеш/StepOperationalFile и очистка 7/30 прежние. Размер содержимого сверяется
с объявленным до сохранения. Opener ограничен tenant и ссылками входа шага;
предельный размер контролируется до чтения/сохранения результата.

`native_io` фиксирует send marker короткой транзакцией и вызывает действие вне
транзакции runner. Файловая запись сама устанавливает tenant. Подтверждённый
result receipt хранит зашифрованный результат и метаданные файлов отдельно от
fenced checkpoint. Сбой после I/O без receipt оставляет unknown; восстановление
не повторяет I/O. Receipt после сбоя checkpoint возвращает прежний файл.
Локальные DB-действия сохраняют прежнюю атомарную границу. Causality проходит
штатным T-172 origin, время учитывается общим бюджетом.

В метаданные отображения `fileNames` добавляется имя принадлежащего шагу файла; хранимые
arguments/result и последующие bindings сохраняют `{"fileId": "UUID"}`.
Общий RunValues отображает имя прежней строкой значения, без нового layout.

## Выполненные проверки

Штатная сборка/миграции `start_environment` пройдены. `manage.py check` — без
замечаний. `makemigrations --check --dry-run` через backend-admin — No changes
detected. Попытка этой же read-only проверки через backend-app получила штатный
permission denied на django_migrations; права не менялись.

Первый адресный backend-прогон: 26 passed, 1 failed, 378.62 с. Прошли реальные
CSV/XLSX, права отчёта, квота/файлы/RLS/retention, два crash-сценария и затронутые
локальные native-комментарии. Ошибка была в новом тестовом диалоге без обязательного
контакта; исправлены только его данные. После дополнения представления имени
файла повторены упавшая проверка и непосредственно изменённый payload/retention:
3 passed, 129.17 с. Хранимый результат остаётся строгой файловой ссылкой.

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_files.py chatballs/integrations/action_catalog/test_native_io.py chatballs/integrations/action_catalog/test_native_comments.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/execution/test_files.py chatballs/integrations/service_connections/test_service_rls.py::ServiceConnectionRuntimeRoleTests::test_file_persistence_and_reads_establish_their_own_tenant_context chatballs/conversations/test_voice_messages.py::VoiceApiTests::test_audio_is_served_to_visible_viewer_only chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short
```

Frontend controlModel.test.tsx: 4 passed. `npm run build --workspace=@chatballs/internal-ui`
повторно прошёл на окончательных исходниках (4643 modules), существующее
предупреждение chunk >500 kB. Финальный controlModel.test.tsx: 4 passed, 63.10 с.

В штатном редакторе проверены шесть локализованных названий и параметр номера
сообщения, скриншот `element-2026-11-04T16-40-41-233Z.png`. Проверочный сценарий
отброшен через «Не сохранять». Реальный CSV запущен через штатный preview/confirmation API; worker завершил
Run b9fa0829-4a7f-4956-82cc-270283687062. В журнале видны «Успешно» и
`support-report.csv`; UUID не показан. Документ 1280=scrollWidth, карточка
740=scrollWidth. Скриншот `element-2026-11-04T19-11-17-326Z.png`.
Нового layout нет. В последней навигации 0 ошибок консоли и одно прежнее
предупреждение; при обновлении backend ранее были прерванные запросы.

Полный набор тестов, внешняя доставка и RTC этим прогоном не проверялись.

## Сбой обновления контура и повтор

Повторный `start_environment` после добавления имени файла в представление
журнала завершился ошибкой Skaro:

```text
EPERM: operation not permitted, rename 'C:\Users\drmar\MyProjects\Chatballs\code\chatballs\.skaro\architecture.md.3e684496-cb2a-4b02-9873-6caee46e5028.tmp' -> 'C:\Users\drmar\MyProjects\Chatballs\code\chatballs\.skaro\architecture.md'
```

Это путь основной копии, которым управляет Skaro. Агент не редактировал его,
не менял права и не запускал сервисы вручную. После команды владельца «попробуй ещё раз» повторный штатный запуск прошёл;
Skaro подтвердил готовность frontend/api/platform/web_chat на прежних
портах 20016/20014/20015/20017. EPERM не повторилась. Повторные проверки
окончательных исходников выполнены; результаты приведены ниже. Это проверка
файловой части, не финальная приёмка всей задачи.


Повтор адресных backend-проверок на окончательных исходниках:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_files.py::NativeFileTests::test_domain_attachment_audio_avatar_and_redacted_diagnostic_use_original_selectors chatballs/integrations/action_catalog/test_native_files.py::NativeFileTests::test_native_file_receipt_replays_and_retention_deletes_only_operational_copy chatballs/integrations/action_catalog/test_native_comments.py::NativeCommentTests::test_runner_appends_internal_once_and_keeps_result_encrypted --reuse-db -q --tb=short
docker compose exec -T frontend npm run test --workspace=@chatballs/internal-ui -- src/features/integrations/scenarios/controlModel.test.tsx
docker compose exec -T frontend npm run build --workspace=@chatballs/internal-ui
```

Ruff всех изменённых Python-файлов и `git diff --check` пройдены. Новых/изменённых
файлов кода длиннее 300 строк нет. После простоя контур был остановлен Skaro;
штатный повтор `start_environment` успешен. Proxy frontend вернул HTTP 200,
database=true, redis=true.


После окончательного завершения повторного start_environment (04.11.2026)
readiness через frontend снова 200 с database=true/redis=true. Сохранённый
реальный Run b9fa0829-4a7f-4956-82cc-270283687062 снова открыт в журнале:
completed, error пуст, fileNames содержит support-report.csv, хранимый result
содержит только строгий fileId. Снимок element-2026-11-04T20-54-51-898Z.png
визуально проверен; документ 1280/1280, карточка 740/740. В этой навигации
0 console errors, 1 прежнее предупреждение WebSocket при переключении страницы.
Показанное уведомление «Состояние запуска изменилось» — прежний 15-секундный
таймер useRunDetail, не ошибка запуска; API детали возвращает 200/completed.
