# Действия организации, контента и управления сценариями — T-175

## Граница реализации

Уточнение принятой SPEC-0037/ADR-0038 для группы T-175. Оба результата baseline лично приняты владельцем 22.10.2026 (R-28). Новых экранов, служебных UI-текстов или изменений ролей для проверки не требуется. Реализованный checkout проверяется отдельно от публикации: эта архитектурная детализация не переводит родительские planned-компоненты и весь этап в current.

Один native registry, прежний runner, PostgreSQL/RLS, inbox/outbox, worker и worker-events. API и действия вызывают одни application services; нет HTTP к себе, dispatch APIView, поддельного Request, нового движка или универсального CRUD. Полный перечень API хранится рядом с кодом в action_catalog/*_inventory.json и проверяется против фактически смонтированного resolver.

На checkout T-175: 274 действия, 310 API/transport-входов (277 продуктовых связей, 33 протокольных). Разница объясняется несколькими API-алиасами одного действия, в том числе наследованием GET. Эта численность описывает проверенный срез, а тест сверяет фактические множества, не прибитое число. Глобальные функции HumanUser/установки/платформы остаются T-176 принятого плана; отдельный auth_boundary_inventory.json классифицирует 24 auth-входа и не называет редактирование профиля протоколом логина.

## Доменные границы

- Организация: employees/groups/availability/settings вызывают штатные службы membership, приглашений, владения, ролей, групп, доступности, аудита, режима и настроек. Сохраняются OWNER/ADMIN, супервизорская область, запрет выдачи global admin через tenant и ограничения многопользовательского HumanUser.
- Контент: agents/skills/knowledge/knowledge_categories/knowledge_links/knowledge_files и portal-модули сохраняют видимость, права изменения, ревизии, публикацию, импорт, индекс и настоящее файловое хранилище. Произвольные примеры навыков остаются данными, не становятся bindings или полномочием на файл.
- Подключения: service_connections/connections используют общие management/management_reads и прежнюю валидацию провайдеров/адресов. Настройки транспорта, AI и виджета доступны по тем же разрешениям; OAuth/callback/выдача credential сохраняют собственный протокол.
- Сценарии: scenarios/agent_policies/run_management/scenario_metadata/synchronization/entity_links используют общие definition management, journal queries, policy management и службы обмена. Редактирование определения не исполняет его; изменение настройки не расширяет principal действующего Run или предков nested-вызова.

Write/delete не сведены к read. Descriptor объявляет effect, required capability, organization/conversation scope, TypeSpec input/output, I/O и retry. Точный grant и политика подтверждения общего runner действуют перед эффектом. Обёртка повторяет доменную проверку, включая канонический диалог для связанных ресурсов. DB-only результат и receipt атомарны; I/O вне транзакции, неоднозначная доставка не считается безопасной для автоматического повторения. Подтверждённый доменный отказ сохраняется как failed без полезных данных; прежний формат completed читается совместимо.

## Секреты и протоколы

Секреты принимаются по типизированному закрытому каналу и не становятся обычным результатом. Definition в аргументах журнала скрывается целиком, возвращаемое определение очищается по схемам шагов; неизвестная схема закрывает входы. Server-side copy сохраняет секретные значения без выдачи клиенту. Native key metadata не содержит одноразовый токен, rotation остаётся интерактивным credential-протоколом. Из результата чтения журнала удаляется editToken.

Native runs.control.post разрешает cancel/reconcile. Approve/edit/revise/release-edit/repeat/resolve/decide — явно перечисленные варианты штатного digest/revision/intent протокола, не обходные вложенные grants. Preview/launch сохраняют общий вход исполнителя; nested-сценарий запускается штатным блоком call с пересечением областей всех предков. Поиск внешнего кандидата вызывает зарегистрированную adapter operation через прежний launch; чтение кандидатов, явный replace/unlink имеют собственные действия. Телефон/email не создают идентичность автоматически.

Retention сохраняет OWNER/ADMIN, ревизию, подтверждение сокращения и 24-часовую задержку удаления. Agent policies сохраняют atomic batch, ревизии всех целей, off/self/ask и явного текущего делегата. Metadata lookup проверяет точную разрешённую операцию; approval lookup — текущего одобрителя и замороженный контракт. Запрет неподдерживаемой условной записи адаптера не ослабляется.

## Общий UI и расширения

Versioned controls structured_value@1 и scenario_settings@1 зарегистрированы в общем реестре. Первый отображает произвольные смешанные примеры через существующие типы/вложенные поля; второй использует принятые ScenarioSections/ScenarioDrawer и хранит {definition, agentPolicies} единым значением. Никакого ветвления ядра по названию действия, обязательного JSON-редактора или выдачи ключа из вложенного контрола. Общий журнал отображает те же TypeSpec результаты после очистки. RU/EN словари и browser-проверка входят в результат.

Сборка frontend и адресные backend/frontend тесты, реальные screenshots и ограничения проверки: docs/verification/T-175/README.md, portals-structured.md, services-files.md, connections.md, scenarios.md. Справка с примерами: docs/native-organization-actions.ru.md/.en.md и docs/native-scenario-actions.ru.md/.en.md. Демо-аккаунты уже существовали; seed, изменение их паролей/ролей, fake backend и временные HTTP-серверы не использовались. Адресные adapter tests не являются заявлением о проверке новых реальных внешних доступов.

## Архитектурное покрытие

Context и container views сохраняют сотрудников/ИИ, существующий монолит и его внешние границы. Component views сохраняют native → identity/availability/AI/skills/knowledge/portals/storage/integrations/webchat/i18n/setup-demo. Code views показывают модули внутри своих компонентов. Упорядоченные dynamic-native-administration/journal/agent-policy/connections/links показывают runner → актуальные права/grants → registry/TypeSpec → соответствующий definition/journal/policy/connections/synchronization service → receipt/checkpoint/recovery. Deployment прежний, новых обязательных служб нет; dev polling/libuv изменяет только производительность существующих frontend bind mounts.

Все уровни context/container/component/code и deployment/dynamic применимы; исключённых уровней нет. Стабильные ID, остальные R-1–R-33, решения по T-174/T-176, речи и событиям сайта сохранены. ADR-0038 управляет native/runner/секретами и неизменной областью полномочий. Точные связи требований обновляются в единственной общей модели, она не копируется в Markdown. Базовая архитектура и её planned элементы не объявляются полностью реализованными этим уточнением.
