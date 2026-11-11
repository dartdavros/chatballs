---
id: T-181
title: Запускать первый ответ агента по событию сайта
milestone: M23
status: done
depends_on:
  - T-180
  - T-178
  - T-172
  - T-174
order: 2
spec: "0040"
created: 2026-11-03
branch: skaro/T-181-zapuskat-pervyy-otvet-agenta-p
archived: true
---

## Цель

Реализовать весь путь явного события сайта: локальное приглашение, согласие/форма, идемпотентный общий сценарий и первый штатный AI-ответ. Сохранить изоляцию посетителя и отсутствие data-запросов/обращений до начала.

## Критерии приёмки

- [x] UI начинается после личной приёмки site-design. WEB-правило name/schema/invitation/scenario/active изолировано по виджету/организации и выключено по умолчанию; публичная проекция не раскрывает internal IDs/ключи. Старые приветствие/setFields/обычный чат не меняют поведения.
- [x] Chatballs.emitEvent({widgetKey,name,eventId,data}) работает до/после загрузки отдельной очередью, с origin/source/instance. Поля не сливаются с событиями и не запускают сценарий неявно; трекинг DOM/scroll не добавлен.
- [x] До согласия локальное приглашение не передаёт data на backend и не создаёт contact/Conversation/Message/Run/AI/unread/звук. Первое событие только в памяти с TTL5мин; sessionStorage хранит техническую отметку. Закрытие/reload/истечение исключают повторный показ/поздний запуск, панель не раскрывается сама.
- [x] Принятие переиспользует общий серверный consent voice-input и обязательную форму. Старый token/флаг/версия не обходят guard. С актуальным согласием допустимый event запускается без повторной формы и первого клиентского текста.
- [x] Backend проверяет active rule/name/schema/20KiB/origin/WebSession/tenant и разрешает только настроенный сценарий своего посетителя без browser API-key/grants/scenario_id. Невалидные data отклоняются без чувствительных логов, rate limits/параллельность действуют.
- [x] После завершения T-172/T-174 webchat.site_event и native-действие первого хода подключены к общим receipt/outbox/fan-out/Run/snapshot/grants/journal. Commit до ACK, event dedup и atomic once-rule-WebSession исключают дубли при новом ID/вкладках/reload/падении; второй runner/служба/HTTP к себе не добавлен.
- [x] Первый ответ использует прежние domain services/AI-orchestrator без фиктивной реплики клиента или второго LLM-цикла. Доверенное задание сценария отделено от недоверенных псевдонимизированных data; без истории язык организации с учётом answer_language.
- [x] Перед эффектом/сохранением/доставкой проверяются mode/agent/consent/rule/grants/control/generation. Обычный первый ввод, перехват или закрытие подавляют поздний проактивный ответ без второго диалога/дубля/переоткрытия. Событие не расширяет полномочия и не подтверждает внешнюю запись.
- [x] Журнал честно показывает запуск/подавление/сбой, виджет не выдаёт технические коды/ложную отправку и сохраняет обычный ввод. Event/action descriptors и классификация новых API дополняют общий каталог.
- [x] Пройдены сборки и целевые тесты очереди/TTL/consent/формы/schema/origin/RLS/dedup/гонок/восстановления/AI-policy/i18n, backend --reuse-db. Browser в штатном контуре подтверждает отсутствие payload-запроса до согласия и один реальный первый ответ после. Справка содержит рабочий emitEvent/eventId/retry/TTL; нет заглушек/seed/смены доступов.

## Заметки

Причина выделения: единый самостоятельно полезный первый контакт; loader/настройка/consent/ingress/native action/гонки/UI/тесты/справка тесно связаны и остаются одной вертикальной задачей. T-172/T-174 обязательны, их общий объём/статусы не меняются (T-171 сейчас failed, последующие blocked). voice-input — владелец общего server-consent, исключает конкурирующие миграции между этапами. Пути: webchat/{site_event_config,site_events,proactive_models,proactive,consent}.py, loader_assets/site_events.js, web-chat/src/proactivity/, integrations/{automation_events,scenarios/native_events.py,action_catalog/webchat.py}, AI-orchestrator. C4: component-webchat-proactivity, code-site-event-loader/widget-site-events/web-site-config/web-site-events/web-proactive, code-service-event-ingress, code-web-consent. Проверки входят в этот результат: для изменений кода сборка затронутых приложений/образов и только относящиеся тесты (backend --reuse-db), UI — браузером в штатном приложении. Полный тестовый прогон только по прямому указанию. Не создавать mock API/fake backend/временные HTTP-серверы/seed, не менять доступы. Отсутствие реального ключа/контура честно фиксировать blocker, не подменять успехом. Соблюдать AGENTS.md, DRY/KISS/SRP/NO GOD FILES, пределы компонентов ≈180–200 и файлов ≈300 строк, composition-only pages, существующие shared-компоненты/спиннер/.link/app-dropdown и ru/en t/tn/fmt. До сдачи get_c4_context и review_c4 по фактическому changeHash/reviewScope, affected IDs и code evidence; изменение поведения требует принятого C4-пакета. Planned не объявлять current до проверенной публикации. Не готовить спецификации или новые задачи в задаче реализации.

## Итог

Реализован полный путь явного события сайта: отдельная очередь emitEvent, локальное приглашение и TTL, общее серверное согласие и форма, идемпотентный ingress и первый штатный AI-ответ через общий runner. В штатном окружении подтверждены отсутствие payload/обращений/AI до согласия и ровно один реальный ответ OpenRouter после него; сборки и адресные проверки прошли, добавлена справка ru/en. Коммиты 15a811c2 и 42cd1061, рабочая копия чистая; принятый C4-пакет применён, review обновлён для ревизии 18 и неизменившегося fingerprint кода.
