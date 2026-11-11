# Внутренние действия общения и обслуживания — T-174

Статус: предлагаемая детализация planned-архитектуры SPEC-0037/ADR-0038.
Принятие пакета разрешает реализацию этой детализации, но не означает
прохождение критериев задачи или публикацию кода.

## Основа и границы

Личная приёмка двух baseline зафиксирована владельцем 22.10.2026:
docs/service-integrations-t167-acceptance.md и SPEC-0037 R-28.
Источники дизайна — принятые .dc.html основной копии проекта; прежний README
в checkout T-174 исторический. Макеты не копируются поверх исходников задачи.
Действия заполняют существующие схемные формы редактора, запуска и журнала,
используют ru/en и существующие компоненты. Новые layout/кнопки не вводятся.

Сохраняются один backend, PostgreSQL/tenant/RLS, worker/worker-events,
штатные файлы и inbox/outbox. Ни один обязательный сервис не добавляется.
Полнота сотрудников/ИИ/знаний/порталов/установки остаётся T-175/T-176;
их существующие и planned IDs не удаляются и не объявляются реализованными.
Область T-174 включает также вспомогательные продуктовые возможности этой
группы: email-продолжение, черновики ответа, политики назначения/очереди,
историю участия, таксономию и права шаблонов, настройки оценок и качества.

## Реестр и проверяемая полнота

ActionDescriptor имеет стабильный ключ chatballs:<domain>.<operation>,
версию контракта, i18n title/description, TypeSpec входа/результата,
класс эффекта, исходную capability/область, execution/recovery policy,
ссылки на продуктовые API-входы и вызываемый доменный сервис.
Параметры именованы и типизированы: нет единого свободного JSON payload.
Схемы используют общие даты/enum/lookup/file/объекты/списки, обязательность,
nullable и ссылки на результаты; бинарные данные передаются штатными файлами.

registry.py отвечает за уникальность и контракт; coverage.py — за сопоставление
реально смонтированных URL + HTTP-метод с descriptor либо точной причиной
непродуктовой классификации. Таблица ниже получена статическим разрешением
imports/наследования из urls_app.py и шести URL-модулей: 127 входов,
из них 125 продуктовых и 2 обмена credentials. Это исходный проверяемый
перечень T-174 на baseHead 6e007519, а не отчёт о зарегистрированных действиях.
Суффикс HTTP-метода в ключе — технический стабильный ID; UI показывает
локализованное продуктовое название.

Coverage при реализации сверяется также с фактическим Django URL resolver,
включая унаследованные методы и alias-пути. OPTIONS/HEAD не становятся
дополнительными бизнес-функциями. Новая функция в этой группе обязана
добавить descriptor: неизвестный method/route, устаревшая ссылка и descriptor
без executable handler проваливают непосредственно затронутый contract test.
Неиспользуемые legacy view-файлы не считаются публичными API без mount.
Внешние webhooks, customer-webchat ingress, realtime и другие транспортные
входы отдельно инвентаризируются по фактическому resolver; причина описывает
конкретную аутентификацию/протокол и связанную доменную возможность.
Если вход содержит самостоятельную продуктовую функцию, он получает descriptor;
объявлять весь модуль transport для сокрытия функции нельзя.

## Доменные сервисы

Небольшие модули action_catalog/conversations, contacts, labels, messages,
comments, media, participants, transfers, calls, notifications, templates,
rules, reports, ratings, quality делегируют штатным сервисам и selectors.
В них нет HTTP к себе, вызова APIView/DRF dispatch, искусственного Request,
универсального CRUD по модели или обхода бизнес-проверок.
При отсутствии сервисной функции соответствующая логика API выносится
в доменный application service с явным TenantContext и именованными параметрами.
Исходный API и действие вызывают эту же функцию. Сериализация/схемы отделены
от поведения, повторяющиеся проверки переиспользуются.

Перед эффектом проверяются текущие membership/роль, tenant, scope, грант,
видимость конкретного ресурса, назначения, ограничения супервизора,
режим/состояние диалога и разрешённость канала. Комментарии и их файлы
сохраняют внутреннюю аудиторию. Личная библиотека шаблонов и собственные
уведомления не становятся данными любого сотрудника организации.
OWNER-only merge и управление качеством/оценками сохраняют исходные ограничения.
Доступ к отчёту и его CSV/XLSX одинаково проверяется доменным сервисом.

Продуктовые token-scoped calls.state/accept/decline/end и ratings.customer
не классифицируются как auth. Их схемы требуют действующий исходный credential
с secret/redaction; организация ресурса должна совпасть с серверным tenant Run,
исходные side/subject/expiry/immutable-vote ограничения повторно проверяются.
Grant сам не выпускает клиентский credential и не разрешает ответить за клиента.
Секреты не попадают в журнал/выход модели. Исключённые два auth-входа не
используются для приобретения новых прав сценарием.

## Общие grants и исполнение

Native не создаёт фиктивный Integration. ScenarioStep.integration уже nullable.
Общий resolver возвращает типизированную ссылку native/service и общий контракт;
snapshot/bindings/preview/approvals/journal/recovery сохраняют общий протокол.
В одном списке шагов свободно сочетаются обе разновидности.

ActionGrant расширяется взаимоисключающими целями: существующее подключение +
service-operation либо native action key без подключения. База обеспечивает
валидность/уникальность обеих форм, tenant и membership; прежние строки
сохраняют прежний смысл, миграция никому не выдаёт разрешений.
Native цель включается в тот же протокол agent grants и automation principal;
наличие навыка, сценария или старого service grant не выдаёт native-полномочия.
Явное делегирование и текущие права пересекаются со snapshot перед каждым эффектом.
Существующие автоматизация T-172 и ИИ T-173 не подменяются отдельным bypass.

Для локального DB-эффекта доменное изменение, result receipt и checkpoint/outbox
фиксируются одной tenant-транзакцией с исходными проверками; rollback не оставляет
ложный успех. Эффект связывается с неизменным step.effect_key и digest контракта/
аргументов. Повтор после commit читает сохранённый исход, а не меняет домен снова.
Receipt хранит чувствительный результат зашифрованно и подчиняется общей очистке
7/30; активные потребители/файлы сохраняют прежнюю защиту.

Действия с внешним I/O не объявляются обычной атомарной записью в PostgreSQL.
Они используют исходный ключ доменной операции и устойчивый send marker,
объявляют конкретную стратегию восстановления. Штатный prepare/run/store
расшифровки сохраняет I/O вне транзакции; DB-only receipt не доказывает
доставку в мессенджер. Вызовы штатных сервисов сохраняют их бизнес-проверки
и согласованные транзакционные границы; runner не оборачивает внешний I/O
своей общей транзакцией. В отсутствие provider idempotency/reconcile падение
после send оставляет unknown без слепой повторной доставки.
Успех показывается только по подтверждённому доменному/транспортному исходу,
а создание сообщения и подтверждённая доставка различаются контрактом.
Существующая доставка через outbox не запускается параллельно новым handler.

Доменный факт публикуется прежним общим hook в исходной транзакции.
Обёртка не публикует второй тот же факт, не регистрирует старые обработчики
или четыре правила повторно. Origin/causality проходят штатным путём T-172,
эхо не запускает обратную цепь; технические бюджеты runner сохраняются.

## Проверка перед приёмкой

Нужны сборка текущих исходников штатного контура; только затронутые backend
contract/coverage и поведенческие --reuse-db проверки и frontend type/build.
Проверяются: текущий membership/роль и межtenant-доступ; невидимый/чужой
диалог; назначение/супервизор; внутренний комментарий и вложение; личные шаблоны;
OWNER merge; отчёт/оценка/quality scope; token side/tenant/expiry и неизменность
оценки; типы/lookup/file/result bindings; смешанный native+service сценарий;
отзыв grant перед эффектом; rollback/crash/recovery и отсутствие второй
доставки/повторного доменного факта/обратного цикла.
Проверки частичных исходов не заменяются положительным HTTP 200.

UI проверяется task-local Playwright в окружении start_environment:
API proxy readiness должна подтверждать именно базу и cache этой задачи.
Используются уже установленные demo accounts без seed и изменения доступов.
Mock API, fake backend и временные HTTP-серверы не создаются.
При отсутствии реального внешнего доступа соответствующая проверка остаётся
открытой; утверждение о готовности не заменяет доказательство.
Каталог и примеры обновляются в docs/scenarios.ru.md/.en.md и пользовательской
справке группы. До submit_result нужны актуальный C4 context, exact changeHash
review и коммит после необходимых проверок.

## Архитектурное покрытие

Контекст — view-service-context, контейнеры — view-service-containers,
компоненты — view-service-backend/workbench, код — view-service-code-native,
policy/runner/state, данные — view-service-data. Развёртывание —
view-service-deployment с теми же backend/worker/PostgreSQL/cache/media.
Новый ordered dynamic-native-actions раскрывает native вызов, грант, сервис,
receipt и возвращение в runner. Existing mixed external/native, recovery и
event/native-sync views сохраняются. Ни один уровень T-174 не исключён.
SPEC-0037 R-1–R-33 и чужие решения/вопросы сохраняются; затронутые R-2/4/9–12/
14–17/19–25/27–31 получают связи с уточнёнными native IDs.
Принятие документа не реализует planned и не закрывает весь этап.

## Исходное соответствие API — planned descriptors

| API-вход | Планируемое действие либо классификация | Доказательство: существующий обработчик |
|---|---|---|
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/quality/settings/` | `chatballs:quality.settings.get` | `chatballs.conversations.quality.views.QualitySettingsView` |
| PUT `/api/v1/organizations/<uuid:organization_public_id>/conversations/quality/settings/` | `chatballs:quality.settings.put` | `chatballs.conversations.quality.views.QualitySettingsView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/quality/report/` | `chatballs:quality.report.get` | `chatballs.conversations.quality.views.QualityReportView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/quality/jobs/<int:job_id>/` | `chatballs:quality.job.get` | `chatballs.conversations.quality.views.QualityJobView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/quality/jobs/<int:job_id>/corrections/` | `chatballs:quality.correction.post` | `chatballs.conversations.quality.views.QualityCorrectionView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/quality/jobs/<int:job_id>/messages/<int:message_id>/` | `chatballs:quality.evidence.get` | `chatballs.conversations.quality.views.QualityEvidenceView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/quality/` | `chatballs:quality.conversation.get` | `chatballs.conversations.quality.views.QualityConversationView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/quality/launch/` | `chatballs:quality.analysis.post` | `chatballs.conversations.quality.views.QualityLaunchView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/activity-history/` | `chatballs:conversations.activity.get` | `chatballs.conversations.activity_views.ConversationActivityView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/participation-journal/` | `chatballs:conversations.participation_journal.get` | `chatballs.conversations.participation_journal.ParticipationJournalView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/participant-limit/` | `chatballs:participants.limit.get` | `chatballs.conversations.participant_views.ParticipantLimitView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/participant-limit/` | `chatballs:participants.limit.patch` | `chatballs.conversations.participant_views.ParticipantLimitView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/participants/` | `chatballs:participants.get` | `chatballs.conversations.participant_views.ParticipantListView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/participants/` | `chatballs:participants.post` | `chatballs.conversations.participant_views.ParticipantListView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/participants/history/` | `chatballs:participants.history.get` | `chatballs.conversations.participant_views.ParticipantHistoryView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/participants/<int:participant_id>/` | `chatballs:participants.member.delete` | `chatballs.conversations.participant_views.ParticipantDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/assignment-policy/` | `chatballs:conversations.assignment_policy.get` | `chatballs.conversations.transfer_views.AssignmentPolicyView` |
| PUT `/api/v1/organizations/<uuid:organization_public_id>/conversations/assignment-policy/` | `chatballs:conversations.assignment_policy.put` | `chatballs.conversations.transfer_views.AssignmentPolicyView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/transfers/` | `chatballs:transfers.history.get` | `chatballs.conversations.transfer_views.TransferHistoryView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/transfers/<int:transfer_id>/` | `chatballs:transfers.history.get` | `chatballs.conversations.transfer_views.TransferHistoryView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/transfer-options/` | `chatballs:transfers.options.get` | `chatballs.conversations.transfer_views.TransferOptionsView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/reply-assistance/` | `chatballs:messages.assistance.get` | `chatballs.ai.assistance_views.AssistanceListView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/reply-assistance/` | `chatballs:messages.assistance.post` | `chatballs.ai.assistance_views.AssistanceListView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/reply-assistance/<uuid:attempt_id>/` | `chatballs:messages.assistance_attempt.get` | `chatballs.ai.assistance_views.AssistanceDetailView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/reply-suggestions/<uuid:suggestion_id>/reject/` | `chatballs:messages.suggestion.post` | `chatballs.ai.assistance_views.AssistanceRejectView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/transfer-reasons/` | `chatballs:transfers.reasons.get` | `chatballs.conversations.transfer_reason_views.ReasonListView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/transfer-reasons/` | `chatballs:transfers.reasons.post` | `chatballs.conversations.transfer_reason_views.ReasonListView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/conversations/transfer-reasons/<int:reason_id>/` | `chatballs:transfers.reason.delete` | `chatballs.conversations.transfer_reason_views.ReasonDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/transfer-reasons/<int:reason_id>/` | `chatballs:transfers.reason.get` | `chatballs.conversations.transfer_reason_views.ReasonDetailView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/transfer-reasons/<int:reason_id>/` | `chatballs:transfers.reason.patch` | `chatballs.conversations.transfer_reason_views.ReasonDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/` | `chatballs:conversations.get` | `chatballs.conversations.read_views.ConversationListView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/stats/` | `chatballs:reports.overview.get` | `chatballs.conversations.reporting_views.ConversationStatsView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/support-report/access/` | `chatballs:reports.access.get` | `chatballs.conversations.support_views.SupportReportAccessView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/support-report/` | `chatballs:reports.support.get` | `chatballs.conversations.support_views.SupportReportView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/support-report.csv` | `chatballs:reports.support_csv.get` | `chatballs.conversations.support_views.SupportCSVView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/support-report.xlsx` | `chatballs:reports.support_xlsx.get` | `chatballs.conversations.support_views.SupportXLSXView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/clients/` | `chatballs:contacts.get` | `chatballs.conversations.reporting_views.ClientsView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/clients/<int:contact_id>/` | `chatballs:contacts.card.get` | `chatballs.conversations.reporting_views.ClientDetailView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/clients/<int:contact_id>/` | `chatballs:contacts.card.patch` | `chatballs.conversations.reporting_views.ClientDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/clients/<int:contact_id>/avatar/` | `chatballs:contacts.avatar.get` | `chatballs.conversations.reporting_views.ContactAvatarView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/conversations/clients/<int:contact_id>/merge/` | `chatballs:contacts.merge.delete` | `chatballs.conversations.reporting_views.ClientMergeView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/clients/<int:contact_id>/merge/` | `chatballs:contacts.merge.post` | `chatballs.conversations.reporting_views.ClientMergeView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/` | `chatballs:conversations.detail.delete` | `chatballs.conversations.read_views.ConversationDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/` | `chatballs:conversations.detail.get` | `chatballs.conversations.read_views.ConversationDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/diagnostic/` | `chatballs:conversations.diagnostic.get` | `chatballs.conversations.diagnostic_views.ConversationDiagnosticView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/claim/` | `chatballs:conversations.claim.post` | `chatballs.conversations.lifecycle_views.ConversationClaimView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/release/` | `chatballs:conversations.release.post` | `chatballs.conversations.lifecycle_views.ConversationReleaseView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/return-queue/` | `chatballs:conversations.return_queue.post` | `chatballs.conversations.lifecycle_views.ConversationReturnQueueView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/messages/` | `chatballs:messages.get` | `chatballs.conversations.message_views.ConversationMessageView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/messages/` | `chatballs:messages.post` | `chatballs.conversations.message_views.ConversationMessageView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/email/options/` | `chatballs:messages.email_options.get` | `chatballs.conversations.email_views.EmailOptionsView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/visitor-state/` | `chatballs:conversations.visitor_state.get` | `chatballs.conversations.visitor_state_views.VisitorStateView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/email/operations/` | `chatballs:messages.email_operations.get` | `chatballs.conversations.email_views.EmailOperationsView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/email/operations/` | `chatballs:messages.email_operations.post` | `chatballs.conversations.email_views.EmailOperationsView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/email/operations/<int:operation_id>/retry/` | `chatballs:messages.email_retry.post` | `chatballs.conversations.email_views.EmailRetryView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/comments/` | `chatballs:comments.get` | `chatballs.conversations.comment_views.ConversationCommentsView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/comments/` | `chatballs:comments.post` | `chatballs.conversations.comment_views.ConversationCommentsView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/request-contact/` | `chatballs:messages.request_contact.post` | `chatballs.conversations.message_views.ConversationRequestContactView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/contact/` | `chatballs:contacts.from_conversation.post` | `chatballs.conversations.conversation_metadata_views.ConversationContactView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/close/` | `chatballs:conversations.close.post` | `chatballs.conversations.lifecycle_views.ConversationCloseView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/spam/` | `chatballs:conversations.spam.post` | `chatballs.conversations.lifecycle_views.ConversationSpamView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/group/` | `chatballs:conversations.group.post` | `chatballs.conversations.management_views.ConversationGroupView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/assignee/` | `chatballs:conversations.assignee.post` | `chatballs.conversations.management_views.ConversationAssigneeView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/priority/` | `chatballs:conversations.priority.post` | `chatballs.conversations.conversation_metadata_views.ConversationPriorityView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/note/` | `chatballs:conversations.note.post` | `chatballs.conversations.conversation_metadata_views.ConversationNoteView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/labels/` | `chatballs:conversations.labels.post` | `chatballs.conversations.conversation_metadata_views.ConversationLabelsView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/archive/` | `chatballs:conversations.archive.post` | `chatballs.conversations.conversation_metadata_views.ConversationArchiveView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/counters/` | `chatballs:conversations.counters.get` | `chatballs.conversations.counter_views.ConversationCountersView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/queue-policy/` | `chatballs:conversations.queue_policy.get` | `chatballs.conversations.queue_policy_views.QueuePolicyView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/queue-policy/` | `chatballs:conversations.queue_policy.patch` | `chatballs.conversations.queue_policy_views.QueuePolicyView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/rules/` | `chatballs:rules.get` | `chatballs.conversations.rules.views.RuleListView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/rules/<str:kind>/` | `chatballs:rules.rule.patch` | `chatballs.conversations.rules.views.RuleDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/rule-executions/` | `chatballs:rules.journal.get` | `chatballs.conversations.rules.views.RuleExecutionListView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/directory/` | `chatballs:conversations.directory.get` | `chatballs.conversations.directory_views.ConversationDirectoryView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/labels/` | `chatballs:labels.get` | `chatballs.conversations.catalog_views.LabelListView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/labels/` | `chatballs:labels.post` | `chatballs.conversations.catalog_views.LabelListView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/conversations/labels/<int:label_id>/` | `chatballs:labels.label.delete` | `chatballs.conversations.catalog_views.LabelDetailView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/labels/<int:label_id>/` | `chatballs:labels.label.patch` | `chatballs.conversations.catalog_views.LabelDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/` | `chatballs:templates.get` | `chatballs.conversations.template_views.ReplyTemplateListView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/` | `chatballs:templates.post` | `chatballs.conversations.template_views.ReplyTemplateListView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/variables/` | `chatballs:templates.variables.get` | `chatballs.conversations.template_variable_views.TemplateVariablesView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/<int:template_id>/render/` | `chatballs:templates.render.post` | `chatballs.conversations.template_variable_views.TemplateRenderView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/permissions/` | `chatballs:templates.permissions.get` | `chatballs.conversations.template_permission_views.TemplatePermissionsView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/permissions/<int:membership_id>/` | `chatballs:templates.management_grant.get` | `chatballs.conversations.template_permission_views.TemplateManagementGrantView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/permissions/<int:membership_id>/` | `chatballs:templates.management_grant.patch` | `chatballs.conversations.template_permission_views.TemplateManagementGrantView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/categories/` | `chatballs:templates.categories.get` | `chatballs.conversations.template_taxonomy_views.CategoryListView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/categories/` | `chatballs:templates.categories.post` | `chatballs.conversations.template_taxonomy_views.CategoryListView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/categories/<int:item_id>/` | `chatballs:templates.category.delete` | `chatballs.conversations.template_taxonomy_views.CategoryDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/categories/<int:item_id>/` | `chatballs:templates.category.get` | `chatballs.conversations.template_taxonomy_views.CategoryDetailView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/categories/<int:item_id>/` | `chatballs:templates.category.patch` | `chatballs.conversations.template_taxonomy_views.CategoryDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/tags/` | `chatballs:templates.tags.get` | `chatballs.conversations.template_taxonomy_views.TagListView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/tags/` | `chatballs:templates.tags.post` | `chatballs.conversations.template_taxonomy_views.TagListView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/tags/<int:item_id>/` | `chatballs:templates.tag.delete` | `chatballs.conversations.template_taxonomy_views.TagDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/tags/<int:item_id>/` | `chatballs:templates.tag.get` | `chatballs.conversations.template_taxonomy_views.TagDetailView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/tags/<int:item_id>/` | `chatballs:templates.tag.patch` | `chatballs.conversations.template_taxonomy_views.TagDetailView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/<int:template_id>/` | `chatballs:templates.template.delete` | `chatballs.conversations.template_views.ReplyTemplateDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/<int:template_id>/` | `chatballs:templates.template.get` | `chatballs.conversations.template_views.ReplyTemplateDetailView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/conversations/templates/<int:template_id>/` | `chatballs:templates.template.patch` | `chatballs.conversations.template_views.ReplyTemplateDetailView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/voice/` | `chatballs:messages.voice.post` | `chatballs.conversations.voice_views.ConversationVoiceView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/<int:conversation_id>/attachments/` | `chatballs:messages.attachment.post` | `chatballs.conversations.attachment_views.ConversationAttachmentView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/messages/<int:message_id>/attachment/` | `chatballs:messages.attachment_file.get` | `chatballs.conversations.attachment_views.MessageAttachmentView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/conversations/messages/<int:message_id>/audio/` | `chatballs:messages.audio_file.get` | `chatballs.conversations.voice_views.MessageAudioView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/conversations/messages/<int:message_id>/transcribe/` | `chatballs:messages.transcription.post` | `chatballs.conversations.voice_views.MessageTranscribeView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/calls/conversations/<int:conversation_id>/` | `chatballs:calls.invite.post` | `chatballs.calls.views.CallCreateView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/calls/conversations/<int:conversation_id>/active/` | `chatballs:calls.active.get` | `chatballs.calls.views.ConversationActiveCallView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/calls/<uuid:call_session_id>/` | `chatballs:calls.session.get` | `chatballs.calls.views.CallDetailView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/calls/<uuid:call_session_id>/cancel/` | `chatballs:calls.cancel.post` | `chatballs.calls.views.CallCancelView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/calls/<uuid:call_session_id>/access-token/` | auth — Обмен действующей сессии сотрудника на краткоживущий токен WebRTC; бизнес-функции звонка представлены calls.invite/session/state/accept/decline/end/cancel. Токен не выпускается сценарием. | `chatballs.calls.views.StaffAccessTokenView` |
| POST `/api/v1/calls/invites/resolve/` | auth — Одноразовый обмен приглашения на клиентский call-access credential; не новая бизнес-команда. Принятие/отклонение/завершение представлены отдельными действиями с исходной проверкой credential. | `chatballs.calls.views.InviteResolveView` |
| POST `/api/v1/calls/access/state/` | `chatballs:calls.state.post` | `chatballs.calls.views.CallAccessStateView` |
| POST `/api/v1/calls/access/accept/` | `chatballs:calls.accept.post` | `chatballs.calls.views.CallAccessAcceptView` |
| POST `/api/v1/calls/access/decline/` | `chatballs:calls.decline.post` | `chatballs.calls.views.CallAccessDeclineView` |
| POST `/api/v1/calls/access/end/` | `chatballs:calls.end.post` | `chatballs.calls.views.CallAccessEndView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/notifications/` | `chatballs:notifications.get` | `chatballs.notifications.views.NotificationListView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/notifications/read/` | `chatballs:notifications.read.post` | `chatballs.notifications.views.NotificationReadView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/notifications/messenger-bindings/` | `chatballs:notifications.bindings.get` | `chatballs.notifications.views.MessengerBindingListView` |
| DELETE `/api/v1/organizations/<uuid:organization_public_id>/notifications/messenger-bindings/<int:integration_id>/` | `chatballs:notifications.binding.delete` | `chatballs.notifications.views.MessengerBindingDetailView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/notifications/messenger-bindings/<int:integration_id>/` | `chatballs:notifications.binding.patch` | `chatballs.notifications.views.MessengerBindingDetailView` |
| POST `/api/v1/organizations/<uuid:organization_public_id>/notifications/messenger-bindings/<int:integration_id>/` | `chatballs:notifications.binding.post` | `chatballs.notifications.views.MessengerBindingDetailView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/notifications/preferences/<str:transport>/` | `chatballs:notifications.preference.get` | `chatballs.notifications.views.NotificationPreferenceView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/notifications/preferences/<str:transport>/` | `chatballs:notifications.preference.patch` | `chatballs.notifications.views.NotificationPreferenceView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/ratings/settings/` | `chatballs:ratings.settings.get` | `chatballs.ratings.tenant_views.RatingSettingsView` |
| PATCH `/api/v1/organizations/<uuid:organization_public_id>/ratings/settings/` | `chatballs:ratings.settings.patch` | `chatballs.ratings.tenant_views.RatingSettingsView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/ratings/results/` | `chatballs:ratings.results.get` | `chatballs.ratings.tenant_views.RatingResultsView` |
| GET `/api/v1/organizations/<uuid:organization_public_id>/ratings/conversations/<int:conversation_id>/` | `chatballs:ratings.conversation.get` | `chatballs.ratings.tenant_views.ConversationRatingsView` |
| GET `/api/v1/ratings/` | `chatballs:ratings.customer.get` | `chatballs.ratings.public_views.PublicRatingView` |
| POST `/api/v1/ratings/` | `chatballs:ratings.customer.post` | `chatballs.ratings.public_views.PublicRatingView` |
## Решение владельца 04.11.2026 — делегат native-разрешения ИИ

В карточке native_ai_principal владелец выбрал «Делегат разрешения».
Это принятое продуктовое решение для планируемой реализации, не проверенный код.
Администратор, явно включающий self/ask native-действия либо сценария с
native-шагами, сохраняется делегатом этого AgentActionGrant. Миграция не
назначает делегата существующим разрешениям: прежние service-операции работают
по прежним правилам, native-эффект без явного делегата запрещён.

Grant имеет ровно одну цель: integration+operation, scenario либо native_key.
Сохраняются off/self/ask, ревизия, серверная привязка агента/диалога/управления
и общий launch/runner. Нет фиктивного Integration или второго исполнителя.
Включение/смена делегата меняет ревизию и отзывает старую привязку; off запрещает
новые эффекты. Миграция не выдаёт разрешений.

Перед native-эффектом policy повторно проверяет grant/revision, конфигурацию
агента, режим организации, управление диалогом, активность делегата и его
сохраняющуюся роль OWNER/ADMIN. Tenant совпадает у агента, grant, делегата, Run
и ресурса. Доменная обёртка получает явный делегированный TenantContext,
исходный сервис повторяет capability, видимость/RLS, назначения и остальные
ограничения. Делегат не назначается ответственным автоматически. Ask-одобритель
не подменяет делегата и не расширяет его полномочия.

У прямой native-операции область следует descriptor (organization либо текущий
conversation/contact), более узкий ActionGrant делегата дополнительно ограничивает
её. В сценарии пересекаются scope снимка/актуального сценария/всех предков,
точная цель agent grant и права делегата. Организационная операция запрещена
в conversation/contact scope. Косвенные ID сообщения/контакта/анализа/звонка
разрешаются исходными сервисами и сверяются с каноническим контекстом.
Grant не выпускает credential клиента и не позволяет действовать за него.

Серверный контекст аудита фиксирует agentId, delegateMembershipId, Run/Step.
Actor/author сотруднических сущностей — реальный явно уполномоченный делегат,
инициатор — ИИ. Контекст ограничен шагом, не протекает в другие запросы.
Личные шаблоны остаются библиотекой делегата; аудитория и история сохраняются.
Обёртка не публикует вторые доменные факты/доставку. Автоматизация T-172
сохраняет своего прежнего явно согласившегося делегата.

В существующем описании карточки «Действия» уточняется смысл разрешения.
Новых layout/кнопок/выбора сотрудника/режимов нет. Согласованный текст:
ru: «Действия Chatballs выполняются от имени администратора, выдавшего
разрешение, с его текущими правами.»
en: “Chatballs actions run on behalf of the administrator who granted access,
using that administrator's current permissions.”
Это согласованное уточнение существующих контролов, без замены baseline.

Адресные проверки должны покрыть direct/scenario native из общего tool-loop,
self/ask, отсутствие делегата, отзыв/смену/revision grant, блокировку/понижение
роли делегата, актуальные назначения/canonical scope, точное подтверждение,
аудит двух субъектов/отсутствие его утечки и повторного эффекта.

Context, containers, components, code/data, deployment и упорядоченные
dynamic-ai/dynamic-native-actions применимы и покрыты прежними views.
Новых обязательных служб нет, ни один уровень не исключён.
R-1–R-33 и прочие planned/current/решения сохраняются.
Уточняются R-14–R-17, R-24 и R-27–R-31 SPEC-0037/ADR-0038.
Реализация и browser-проверка этого решения ещё не выполнены.

## Дополнение T-175 — 05.11.2026

Следующая группа того же registry описана в docs/service-native-organization-runtime.md: организация, сотрудники/membership, контент, подключения и разрешённое управление сценариями. Исторические числа и статусы выше относятся к проектированию T-174; проверенный срез T-175 содержит 274 действия и 310 inventory-входов, отдельную классификацию auth и границы runner-протоколов. Расширение сохраняет принятое решение о явном делегате и не выдаёт tenant-сценарию установочные или глобальные личные полномочия. Детальные build/test/browser результаты — docs/verification/T-175. Публикация и завершение этапа определяются сервисным результатом Skaro, не этой записью.
