# T-173: проверки действий агента — 03.11.2026

Реализация находится в ветке задачи. Полная приёмка не заявляется: реальные
внешние действия и наполненные состояния UI требуют сервисного подключения.
Архитектурный пакет `skaro-c4-48e5ca73-409f-42e3-adb2-8bff9050306b` принят
владельцем и применён Skaro, revision 12; после принятия problems=[].
Planned не объявляется current этим документом или локальным коммитом.

## Реализованный объём

Явные AgentActionGrant одной пары, общая политика карточки/редактора,
существующий ограниченный tool-loop и общий launch/runner, точное подтверждение
и редактирование текущего запроса, durable expiry, маскирование, ID/статус
долгого запуска и проверки перед дальнейшим ответом. Монотонное управление
диалогом и fingerprint агента предотвращают оживление прежнего запуска после
перехвата/возврата или смены конфигурации. Preview и реальный проверочный запуск
явно разделены. Справка: agent-actions.ru.md и agent-actions.en.md.

Личная приёмка обоих baseline от 22.10.2026 проверена по R-28 и документам
приёмки Skaro; карточка плана не использовалась вместо приёмки макета.
Источник UI — принятые «Агент · действия.dc.html» и «Запуск из диалога.dc.html»
основной копии. Существующие знания, навыки и настройки агента сохранены.

## Штатное окружение

Skaro Compose `skaro-chatballs-t-173`: frontend http://localhost:20010,
API http://localhost:20013, platform http://localhost:20009,
web-chat http://localhost:20011. Backend-admin добавлен через штатное
configure_environment; проверки выполняются через compose exec без host-порта.
Readiness через frontend: HTTP 200, database=true, redis=true.
`VITE_DEV_API_TARGET=http://backend-app:8000`; PostgreSQL и Redis healthy.
Использован существующий демо-ADMIN из манифеста. Seed, изменение пароля,
ролей или доступа, временные серверы и fake backend не применялись.

Read-only запрос к действующей копии данных подтвердил: в организациях
1/3/4/5 нет SERVICE-подключений и сценариев. Отсутствие реального доступа
не заменяется автоматическим контрактным адаптером из тестовой базы.

## Выполненные команды

В task-local Compose выполнены:

```text
docker compose exec -T frontend npm --workspace @chatballs/internal-ui run build
docker compose exec -T frontend npm --workspace @chatballs/internal-ui test -- src/features/agents/test-chat/model.test.ts src/features/agents/test-chat/TestChatFeed.test.tsx
docker compose exec -T backend-admin python -m pytest chatballs/ai/test_tool_loop.py chatballs/conversations/test_tool_call_events.py chatballs/integrations/execution/test_ai_bridge.py chatballs/integrations/execution/test_ai_runtime.py chatballs/integrations/execution/test_ai_scenarios.py chatballs/conversations/test_operation_mode_turns.py chatballs/conversations/test_operation_mode_delivery_race.py chatballs/i18n/tests.py --reuse-db -p no:cacheprovider -q --tb=short -x
docker compose exec -T backend-admin python manage.py check
docker compose exec -T backend-admin python manage.py makemigrations --check --dry-run
git diff --check
```

Сборка: exit 0, 4635 modules, Vite 1m55s; остаётся предупреждение о chunks
больше 500 kB. Frontend: 9 passed в двух файлах. Backend: 69 passed, 1 штатный
skipped, 614.52s. Django check без ошибок; миграции — No changes detected.
Ruff для новых AI execution-модулей и затронутых AI orchestration-модулей —
All checks passed. Whitespace-проверка без ошибок.

После окончательного start_environment дополнительно проверены три ручных
сценария общего runner: `ExecutionTests::test_confirmed_effect_is_not_repeated_and_io_has_no_transaction`,
`ExecutionTests::test_exact_approval_is_required` и
`RecoveryAccessTests::test_revoked_actor_cannot_start_a_new_effect` из
execution/test_execution.py и execution/test_access_recovery.py:
3 passed, 64.20s, с теми же --reuse-db и -p no:cacheprovider.

Покрыты явный self для записи без общего подтверждения, preview без Run/outbox,
отзыв, смена режима/агента, перехват и возврат, точный digest/истечение,
блокировка сотрудника, конкурентные решения, редактор только текущего Step,
доступ модели к исправлениям, маскирование и отсутствие значений в журнале,
RLS/FK другой организации, pending/status и отзыв перед ответом, общий budget,
атомарное сохранение grants с ревизией, видимость Run после ошибки провайдера,
прежние HTTP/MCP tool-loop и каталог i18n.

Старые тесты tool-loop приведены к действующей политике: активный провайдер
и явная поддержка инструментов сценарной моделью. Проверка realtime выполняет
commit-callback. Рабочие guard и права ради тестов не ослаблялись.
Полный набор проекта не запускался. Новые модули разделены по ответственности;
новых/расширенных workflow-файлов свыше 300 строк нет. Большие существующие
каталоги переводов не являются компонентами workflow.

## Browser и открытые проверки

В штатном приложении проверены пустая карточка действий, отключённое сохранение,
композиция агента, preview по умолчанию, явный execute и предупреждение,
возврат в preview и ответ существующего встроенного DEMO-провайдера.
При 1024 документ и карточка не имеют горизонтального переполнения.
Это не внешний LLM и не проверка реального сервисного эффекта.
Пустая карточка осмотрена при 1440/1024 в светлой и тёмной теме; при 1024
scrollWidth документа равен 1024, карточки — её clientWidth 520. Реальный Run API
после preview-диалога вернул count=0. После окончательного перезапуска ошибок
консоли на проверенных экранах нет. Ранее встреченный 409 email/options относится
к существующему диалогу; отказы соединения возникали во время остановки сервисов.

Не проверены реальные запись/удаление и длительный внешний результат,
справочники, карточка точного подтверждения/редактор с реальными параметрами,
их мобильная компоновка, конкурентная работа сотрудников в браузере.
Без SERVICE-подключения наполненные состояния не объявляются пройденными.
Окончательный C4 review и вердикты критериев хранятся в Skaro по changeHash;
этот документ не заменяет review_c4/submit_result и не завершает этап.
