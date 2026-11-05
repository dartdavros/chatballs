# T-174: транспортные входы и обратная связь

## Объём

Каталог дополнен отклонением звонка из виджета по существующему WebSession.
Общий resolver сохраняет проверку маршрута, организации, idle TTL и продление
сеанса. Команда не выпускает WebSession/call-access credential; исходный сервис
проверяет канонический диалог перед переходом состояния. Повтор восстанавливает
квитанцию, а секрет скрыт в payload журнала.

Инвентаризация расширена с исходных 127 HTTP-входов до 155 входов: 127 продуктовых
соответствий 125 исполняемым действиям и 28 объяснённых исключений. Включены
14 HTTP-входов SDK и 14 событий/команд WebSocket. Команда завершения звонка
через WebSocket ссылается на то же действие и исходный finish_call. Handshake,
SDP/ICE, telemetry и клиентский ingress классифицированы отдельно: сценарий
не имитирует физическое соединение или происхождение клиентского сообщения.
Coverage сопоставляет записи с реальными mounted HTTP methods, socket routes,
consumer classes и именами обрабатываемых frames.

Отчёт обслуживания имеет типизированные customerRatings/qualityAnalysis как
в общем результате, так и у сотрудников. Сохраняются шкалы, версии, исходные
и исправленные выводы, attribution, интервалы и cohort отправленных запросов.
Ключевые распределения представлены списком value/count, неоднородные значения
качества — теми же typed scalar objects, что в действиях качества.
Исходный HTTP-ответ отчёта не меняется. Положительная доля остаётся доступной
только для объявленной двоичной текстовой шкалы по правилам domain service;
неоднородная шкала не получает выдуманный агрегат.

Общий журнал показывает подписи enum, включая числовые значения, и безопасную
подпись неизвестных диагностических кодов, сохраняя сам код в typed данных.
Дополнительный layout не создаётся. Текущая область сохранённого сценария
и каждого предка пересекается со snapshot/grant перед новым native-эффектом.
Наличие сценария по-прежнему не заменяет exact ActionGrant сотрудника.

## Проверки 05.11.2026

Skaro start_environment собрал и запустил штатный контур. Readiness через
frontend вернул HTTP 200, database=true, redis=true. Адреса: frontend
http://localhost:20016, API http://localhost:20014. Использована существующая
демо-учётная запись, без seed/reset/изменения прав. Тестовые данные создаются
только штатными fixtures изолированной pytest БД.

Первый адресный прогон: **35 passed, 3 failed, 409.44 с**. Ошибки:
две новые проверки передавали numeric positiveValue, запрещённый исходным
сервисом, и отсутствовал ru/en ключ native.fields.corrected. Исправлены
ожидания и схема без изменения исходного бизнес-правила. Добавлена проверка
объявленной двоичной текстовой шкалы и её исправления.

Команда первого прогона:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/i18n/tests.py::CatalogTests chatballs/integrations/action_catalog/test_native_widget_calls.py chatballs/integrations/action_catalog/test_native_calls.py chatballs/calls/tests/test_flow.py::WebchatCallFlowTests chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_idle_session_stops_being_accepted chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_active_session_keeps_renewing_itself chatballs/webchat/test_observations.py::VisitorObservationApiTests::test_only_current_session_credentials_are_accepted chatballs/integrations/action_catalog/test_native_quality.py chatballs/integrations/action_catalog/test_native_reports.py chatballs/integrations/action_catalog/test_native_ratings.py::NativeRatingTests::test_support_feedback_preserves_rating_distribution_and_sent_request_cohort chatballs/integrations/action_catalog/test_native_scope.py chatballs/integrations/action_catalog/test_native_composition.py --reuse-db -v --tb=short
```

Frontend: **5 passed**, команда:

```sh
docker compose exec -T frontend npm --workspace @chatballs/internal-ui test -- src/features/integrations/scenarios/controlModel.test.tsx
docker compose exec -T frontend npm --workspace @chatballs/internal-ui run build
```

Сборка прошла: tsc и Vite, 4643 модуля, 2м20с. Предупреждение о больших chunks
сохраняется. Ruff проходит; изменённых Python/TSX файлов длиннее 300 строк нет.

Реальный отчёт запущен через штатные preview/confirmation API, Run
69a2601f-2582-4d84-ad8c-dabecdeb944d завершён worker успешно. HTTP 200,
customerRatings/qualityAnalysis доступны. В демо за выбранный период нет
оценок/анализов; положительные данные проверяются runner-тестами, а не seed.
В журнале видны подписи состояний/периодов/единиц и причина неполной истории.
Документ 1280=scrollWidth, detail 740=scrollWidth. Консоль: 0 errors,
одно существующее предупреждение WebSocket при навигации. Скриншот
page-2026-11-04T22-05-42-416Z.png выявил ещё raw WEB в деталях — схема
исправлена на общий переводимый enum; это требует повторной browser-проверки.
Проверочный черновик редактора отброшен через «Не сохранять».

Первый повтор: **12 passed, 2 failed, 1 teardown error, 124.01 с**. Пройдено
сохранение смешанной шкалы с отклонением запрещённого reporting, оба исходных
отчётных ограничения, полный coverage и i18n. Заполненные отчёты выявили две
ошибки новой обёртки: общий/персональный feedback разделяли ссылки на строки,
а transport старого события мог быть null. Presenter теперь независимо копирует
каждую секцию feedback; nullable transport сохраняет отсутствие сведений.
Ошибки не скрыты заменой значений или изменением исходного сервиса.

Финальный адресный повтор: **9 passed, 98.49 с**. Проверены заполненные
смешанные/двоичные шкалы, исходные и исправленные выводы, attribution,
клиентские оценки/cohort, ограничения отчёта и все 155 записей coverage.
Предыдущий успешный повтор i18n (5 проверок) остаётся актуальным: после него
переводы не менялись. `manage.py check` — без замечаний.

После финального start_environment readiness снова HTTP 200 с database/redis.
Свежий Run f6e60c09-b781-45d8-89d4-7a3fa10b75ec успешно завершён. Browser
показывает «Виджет сайта» вместо WEB, новые подписи feedback и единиц;
скриншот page-2026-11-04T22-16-36-045Z.png визуально проверен. Старый Run
69a2601f сохраняет прежнюю immutable outputSchema; данные не переписаны.
Форма «Отклонить звонок в веб-виджете» использует обычные схемные контролы:
секретное значение имеет input type=password. Панель 480/480, документ
1280/1280, detail отчёта 740/740. Скриншот
element-2026-11-04T22-17-18-782Z.png визуально проверен. Ошибок консоли нет,
одно прежнее WebSocket warning при навигации. Новый черновик отброшен.

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_quality.py::NativeQualityTests::test_support_feedback_retains_mixed_scales_corrections_and_employee_attribution chatballs/integrations/action_catalog/test_native_quality.py::NativeQualityTests::test_support_feedback_preserves_declared_binary_positive_rate chatballs/integrations/action_catalog/test_native_ratings.py::NativeRatingTests::test_support_feedback_preserves_rating_distribution_and_sent_request_cohort chatballs/integrations/action_catalog/test_native_reports.py chatballs/integrations/action_catalog/test_catalog_coverage.py --reuse-db -v --tb=short
```

Пакет AI native principal skaro-c4-59265996-5fff-40b7-8b7c-996aa36b8e0f
лично принят владельцем и применён Skaro, revision 15. Результаты реализации
и проверок делегата описаны в service-integrations-t174-ai-verification.md.
Этот отчёт не является завершением всего этапа.
