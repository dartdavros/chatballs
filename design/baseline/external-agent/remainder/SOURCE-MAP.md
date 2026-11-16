# Источники компонентов оставшегося комплекта

Источник существующего визуального решения — текущий код приложения. Старые неактуальные макеты не используются. Принятые S01–S06 переиспользуются как неизменяемые новые подвиды там, где они уже соответствуют этому коду. Предлагаемые состояния и тексты внешнего исполнения остаются предметом общей личной приёмки.

Таблица описывает фактическое переиспользование компонентов или их презентационной разметки. Она **не** означает, что источник уже реализует внешний контракт, а его сетевые hooks запущены в макете. Пути ниже даны от корня репозитория; локальные пути групп — от `design/baseline/external-agent/remainder/`.

## Общая оболочка и контролы

| Элемент кадров | Презентация в комплекте | Действующий источник |
|---|---|---|
| Основной сайдбар и пользователь/организация | `agent/AgentSuite.tsx`, `settings/SettingsSuite.tsx`, `chat/ChatSidebar.tsx`; принятые `../agent-external/AgentWorkbenchSidebar.tsx`, `../settings-off/WorkbenchSidebar.tsx` | `apps/internal-ui/src/layout/OrganizationSwitcher.tsx`, `SidebarNavigation.tsx`, `SidebarUserMenu.tsx`, `NavigationIcon.tsx`, `layout/styles.css` |
| Субменю настроек и пункт в конце «Обслуживания» | Принятый `../settings-off/ExternalSettingsNavigation.tsx` | `apps/internal-ui/src/features/settings/SettingsNavigation.tsx`, `navigation.ts`, `navigation.css`; существующая иконка `server` из `shared/icons.tsx` |
| Типографика, тема и акценты рабочего места | Общий runtime; существующие CSS компонентов | `apps/internal-ui/src/styles.ts`, `styles/base.css`, `shared/appearance.ts`, `packages/ui/src/theme.ts` |
| Формы, селекторы, переключатели и кнопки | Все группы | `apps/internal-ui/src/shared/form-controls.tsx`, `ui-controls.tsx`, `ui.tsx` |
| Ссылки и меню | `ExecutionState`, `ConnectionCard`, `GuardedAgentHeader` | `apps/internal-ui/src/shared/links.css`; antd `Dropdown` с `overlayClassName="app-dropdown"`, `.row-menu-button` |
| Подтверждение опасного/значимого действия | `settings/SecurityStates.tsx` | `apps/internal-ui/src/shared/DecisionDialog.tsx`, `shared/ui-controls.tsx` |
| Статусы, загрузка, ошибка и отсутствие прав | `settings/SettingsBody.tsx`, `ConnectionCard.tsx`, `FeatureCard.tsx` | `StatusPill`, `ContentState`, `LoadingState` из `apps/internal-ui/src/shared/ui.tsx`; `shared/icons.tsx` |
| Общий индикатор и строка ожидания | `agent/TestVariantFeed.tsx`, `chat/ChatFeed.tsx`, состояния проверки/сохранения | `LogoSpinner` из `apps/internal-ui/src/shared/icons.tsx` → `packages/ui/src/loader/Loader.tsx`; разметка `features/integrations/services/connect/OAuthWaiting.tsx`, `.service-oauth-waiting` из `services.css` |

## Настройки: S20–S39, S72–S73

| Элемент | Локальный исходник | Источник компонента/паттерна и предел переиспользования |
|---|---|---|
| Включение, сохранённая выключенная конфигурация, повторное включение и ошибка включения | `settings/FeatureCard.tsx`, `SettingsBody.tsx` | `features/settings/styles.css`, текущие `administration-card`, `settings-card-head`, `SwitchButton`, сообщения состояния. Семантика редкой возможности — новое предложение по ТЗ |
| Подключение, адрес, два направления доступа и проверка | `settings/ConnectionCard.tsx` | `shared/form-controls.tsx`; `features/integrations/services/connect/ServiceConnectModal.tsx`, `ServiceAlert.tsx`, `services.css`. Эти формы не переносят исполнителя в CRM-каталог |
| Привязки агентов и внешний ID | `settings/BindingCard.tsx` | Текущие `SelectField`/`FormField`, группы полей настроек. В карточке агента эти формы не повторяются |
| Сроки обработки и инициатива | `settings/ProcessingCard.tsx` | Текущие числовые поля и `SwitchButton`; эксплуатационные значения показаны как пример, без объявления API-defaults |
| Цель конкретной политики | `settings/PolicyTarget.tsx` | Текущие `FormField`/`SelectField`: явные подключение и агент. Не создаёт общего разрешения для всех привязок |
| Стандартные/кастомные поля и различение источников | `settings/DataPolicyCard.tsx` | Таблицы и CSS из `features/integrations/site-fields/ContactFieldsTable.tsx`, `CustomFieldsTable.tsx`, `CustomFieldRow.tsx`, `styles.css`; переключатели — `shared/form-controls.tsx`. Смысл разрешения новый: прежний `aiAccess` не наследуется |
| Разрешённые шаблоны, пустой каталог и устаревшие версии | `settings/TemplatePolicyCard.tsx` | Текущие строки `.service-preset`, карточки настроек и стандартный `SwitchButton`. Это выбор разрешений, не новый редактор шаблонов |
| Однократный показ нового ключа | `settings/SecurityStates.tsx` | Презентационный паттерн `features/employees/EmployeePasswordDialog.tsx`, `.employee-password-field` из `styles-create.css`. Используется недействительный текстовый пример, без генерации секрета |
| Замена/отзыв ключа и выключение возможности | `settings/SecurityStates.tsx` | Настоящий `DecisionDialog` и стандартные кнопки; действия не выполняются |
| Загрузка, отказ загрузки, сохранение, ошибка, права | `settings/SettingsBody.tsx` | `shared/ui.tsx`, стандартные сообщения и `.administration-actions`; сетевых запросов конфигурации нет |

## Агент и проверочная панель: S07–S19, S70–S71

| Элемент | Локальный исходник | Действующий источник |
|---|---|---|
| Колонки, порядок общих секций и заголовок | `agent/AgentSuite.tsx`, `GuardedAgentHeader.tsx` | `features/agents/AgentDetailPage.tsx`, `AgentHeader.tsx`, `model.ts`, `styles.css`; disabled-контролы внешней неготовности — предложенное состояние |
| Встроенные инструкции и модель | `agent/BuiltinViews.tsx` | Настоящие `features/agents/InstructionsCard.tsx`, `ModelCard.tsx` |
| Навыки, знания, действия и инструменты | `agent/BuiltinViews.tsx` | Настоящие `KnowledgeCard.tsx`, `AgentToolsCard.tsx`, `skills/SkillsModelWarning.tsx`; презентационная разметка `skills/AgentSkillsCard.tsx` и `agents/actions/AgentActionsCard.tsx` без их загрузчиков |
| Имя, группа и клиентские подключения | `agent/AgentSuite.tsx` | Настоящие `features/agents/AssignmentCard.tsx`, `ConnectionsCard.tsx` с неисполняемыми callbacks |
| Селектор исполнения, готовность и переход к настройкам | `agent/ExecutionState.tsx` | Текущие `SelectField`, `StatusPill`, сообщения и `.link`; готовые CRM/LLM/tools не выдаются за внешних исполнителей |
| Отдельные язык и STT/TTS | Принятые `../agent-external/ResponseLanguageCard.tsx`, `SpeechCard.tsx` | Текущие контролы `InstructionsCard.tsx`, `SpeechSettings.tsx`, `SynthesisSettings.tsx`; наследование STT «Как у ответов» во внешнем режиме не предлагается |
| Независимая помощь сотруднику | `agent/AssistanceView.tsx` | Презентация `features/agents/AssistanceCard.tsx`, `assistance.css`; локальная подпись устраняет ссылку на скрытый блок модели при S70 |
| Панель проверки, фокус/Esc, шапка и композер | `agent/TestVariantPanel.tsx` | `features/agents/test-chat/AgentTestPanel.tsx`, `styles.css`; `useAgentTestChat` не монтируется |
| Ответ, ошибка, ожидание, прекращение обработки | `agent/TestVariantFeed.tsx` | Настоящий `test-chat/TestChatFeed.tsx`; ожидание — существующий `OAuthWaiting`-паттерн без OAuth-действий |
| Разрешённые тестовые поля | `agent/TestClientFields.tsx`; принятые пустые подвиды S05/S06 | Настоящий `test-chat/TestClientField.tsx`, разметка `TestClientData.tsx`. Нельзя использовать исходные обещания preview о маскировании/несохранении для внешнего исполнения |

## Чат сотрудника: S40–S54

| Элемент | Локальный исходник | Действующий источник |
|---|---|---|
| Оболочка списка/ленты/контекста | `chat/ChatSuite.tsx` | `features/conversations/ConversationWorkspace.tsx`, `ConversationThread.tsx`; `features/sales/dialogs/` и текущие CSS раздела |
| Список диалогов и шапка | `chat/ChatList.tsx`, `ChatHead.tsx` | Презентация `features/conversations/DialogList.tsx`, `DialogListItem.tsx`, `ConversationThread.tsx`; `ContactAvatar.tsx`, текущие статусы и `providerMeta` |
| Карточка контакта и управление диалогом | `chat/ChatContext.tsx` | Презентация `features/sales/dialogs/context/ClientContext.tsx`, `features/conversations/DialogControls.tsx`, `WaitingBlock.tsx`, `features/sales/dialogs/context.css` |
| Обычные/внутренние сообщения и события | `chat/ChatMessages.tsx`, `ChatFeed.tsx` | Настоящие `features/conversations/MessageBubble.tsx`, `ConversationText.tsx`; существующий `.sales-event-chip`. Внутренняя подпись различает внешний handoff и платформенные диагностические сведения |
| Составной ответ и вложения | `chat/MultipartReply.tsx` | `features/conversations/FileMessage.tsx`, настоящий `MessageBubble`, `ConversationText`; картинка из `apps/internal-ui/public/hero.png`, без скачивания внешних URL |
| Оформленный WEB-ответ и текстовый Telegram-вариант | `chat/template-data.ts`, `MultipartReply.tsx`, `ChatFeed.tsx` | `packages/ui/src/messages/PreparedMessage.tsx`, `features/conversations/snapshot-message.css`, настоящий `ConversationText` с `syntax="telegram"` |
| Неизвестная/частичная отправка | `chat/ChatMessages.tsx`, `ChatFeed.tsx` | Та же геометрия исходящего сообщения без стандартной успешной отметки для неизвестного результата; новая диагностическая подпись предложена по ТЗ |
| Голосовое и состояние распознавания | `chat/VoiceBody.tsx` | Презентация `features/conversations/VoiceMessage.tsx`, существующие voice-классы и `voiceWaveHeights` из `@chatballs/ui`; media/STT не запускаются, расшифровка не придумана |
| Композер | `chat/ChatComposer.tsx` | Настоящие `ComposerAudienceBar.tsx`, `ComposerWarning.tsx`, `ComposerDraftButton.tsx`, `EmojiPicker.tsx`, `features/reply-templates/TokenEditor.tsx`; сетевые, файловые и аудиооперации не подключены |

## Клиент: S60–S63

| Элемент | Локальный исходник | Действующий источник |
|---|---|---|
| Размер/позиция окна, мобильный полноэкранный вид | `client/ClientSuite.tsx` | `apps/backend/chatballs/webchat/loader_assets/runtime.js`: desktop до 440×720, right 24/bottom 92 при launcher 56; до 480 px — полный кадр |
| Изоляция собственного документа и CSS | `client/ClientSuite.tsx`, `ClientDocument.tsx` | Shadow DOM сохраняет границу настоящего iframe; настоящие `apps/web-chat/src/WidgetStyles.tsx`, `styles.css`, `widget.css`, `preChat.css`, `consent.css`, speech CSS |
| Шапка, согласие и начало чата | `client/ClientDocument.tsx` | Настоящие `apps/web-chat/src/ChatHeader.tsx`, `ChatBody.tsx` → `ConsentText.tsx`, `StartChatFooter.tsx` |
| Форма перед чатом | `client/ClientDocument.tsx` | Настоящие `PreChatForm.tsx`, `PreChatField.tsx`, `preChatModel.ts`; стандартные поля имени/email и текущая обязательность |
| Условно принятое актуальное согласие и композер | `client/ClientDocument.tsx` | Настоящие `ChatBody.tsx`, `ChatComposer.tsx`, `BrandFooter.tsx`; `useWidgetConsent`/`useChatSession` не монтируются |
| Голосовое после отсутствия/ошибки STT | `client/ClientVoiceBody.tsx` | Настоящие `VoiceMessage.tsx`, `Bubble`-разметка из `ChatMessages.tsx`, `SystemMessage`; URL аудио пуст, клики перехвачены |
| Предлагаемый текст и техническая проверка версий | `client/copy.ts`, `README.md` | Исходный default — `apps/backend/chatballs/i18n/messages/ru.py`/`en.py`, `webchat/configuration.py`; текущая семантика — `apps/web-chat/src/useWidgetConsent.ts`, `consentApi.ts`, backend `webchat/pre_chat.py`, `consent.py`. Это источники аудита, их операции не выполняются |

## Средства просмотра и проверок

`shared/canvas.tsx`, `shared/registry.tsx`, `shared/metadata.ts`, `shared/copy.ts` и `shared/runtime.tsx` относятся к просмотру дизайна: выбор кадра, языка, ширины, темы и акцента находится вне продукта. `build.mjs` формирует локальные ресурсы/экспорты и описание исходников; `check-browser.mjs` проверяет статический документ. Они не запускают проект или внешний сервис.

Новые тексты хранятся отдельно в `agent/copy.ts`, `settings/copy.ts` и его модулях, `chat/copy.ts`, `client/copy.ts` (`clientCopy`), `shared/copy.ts`; старые строки берутся из текущих ru/en-словарей приложений. Сводный состав словарей задан в `shared/metadata.ts`. В продуктовые словари изменения не вносятся.

Правка по замечаниям владельца: `shared/HelpTrigger.tsx` использует штатный antd Modal и малую геометрию/классы `CreateAgentModal` (440 px), Lucide `CircleHelp` отрисован тем же способом, что и Lucide-иконки `shared/icons.tsx`. Пояснения ru/en — `shared/help-copy.ts`. `TemplatePreview` использует штатный `PreparedMessage` и существующее оформление карточки backend `ai/skill_templates/order_sources.py`; пример статуса уже применялся в `chat/template-data.ts`. Приветствие — иллюстративный текст в той же карточке. Ссылки под названиями открывают соответствующий локальный просмотр, поскольку реальный редактор SkillTemplate не имеет отдельного deep-link на шаблон; вымышленные ссылки на записи организации не создаются. Это оформленные сообщения навыков, а не библиотека текстовых быстрых ответов.

`settings/BindingCard.tsx`/`BindingRow.tsx` управляют локальными данными без API и сохранения. `BindingAddDialog` использует штатный Modal/agent-create-* (440 px), `BindingRemoveDialog` — настоящий DecisionDialog danger/trash. `BindingModel` отделяет выбор доступных агентов и проверку/trim ID. `KeyCopyButton` переиспользует Icon, существующие copy/check glyphs и словари; его локальное состояние выполняет явное требование владельца о 18 px, прозрачности и трёх секундах check. Стандартный CopyButton с 13 px/1.2 секунды для этого больше не используется.

`SettingsLoadState` и `SettingsSaveFooter` используют настоящий ServiceAlert и LogoSpinner. Компактный footer и stack gap находятся в `settings/state-layout.css`; видимый busy primary — существующий паттерн `features/support-reports/export.css:28`. Прямые key-actions используют штатные secondary/danger-outline с refresh/xCircle. `form-spacing.css` задаёт 18 px после разделителя, 16 px между предупреждением/полями и пояснением/таблицами. Стек FeatureCard задаёт 12 px между error, warning и badge. Продуктовые стили не меняются.

Новые общие требования владельца о ссылках и правой колонке реализованы один раз в `shared/design-system.css`, подключённом всем новым кадрам. Базовый `.link` сохранён: второстепенные ссылки 12.5 px/500, hover underline dotted без изменения layout; имена сущностей сохраняют свою роль. `.ui-switch-column`/`.ui-switch-cell` задают правое выравнивание заголовка/ячейки, автоматический начальный margin выравнивает сам переключатель.

Полный список зависимостей и хешей конкретной сборки — `generated/sources.json`, перечень кадров — `generated/cases.json`. Таблица покрытия — `COVERAGE.md`. Результаты браузерной проверки и снимки ведутся отдельно в `verification/`; этот документ не утверждает прохождение runtime- или интеграционной приёмки. Формулировка согласия, действующий custom-текст WEB-подключения и юридическая достаточность описаны как открытая граница в `client/README.md`.
