# T-189: защищённый контекст, WEB-поля, история и стенограммы

Проверки 16.11.2026 в основной рабочей копии, вход T-188:
`101bdd7f6c444879652337089988cdbe32d218d6`.

## Реализованный объём

- Отдельные explicit allowlist стандартных и кастомных полей. Полный
  `customFields.mode=replace` с парами sourceConnectionId/fieldId, текущими
  определениями, всеми восемью типами, set/unset/invalid и реальными updatedAt.
  aiAccess встроенной LLM не выдаёт разрешений экспорта.
- PostgreSQL JSON numbers читаются без промежуточного float. Значения, UUID,
  время снимка, полный request и keyed digest фиксируются до HTTP и шифруются.
  Retry/restart использует прежние bytes. Новый ход читает свежий контакт под
  его штатной блокировкой; изменение значения не запускает внешний обмен.
- Отдельная durable `web_schema_generation` повышается DB trigger в той же
  транзакции, что и определения/источник/доступность. Fingerprint включает
  generation, текущую схему и allowlist; A→B→A не оживляет полномочие.
- Политика входит в действующую серверную WEB form revision согласия и во все
  проверки request/cursor/result/delivery. Комментарии и технические записи,
  чужие поля, плохие исходные значения и секреты в контекст не входят.
- История фиксирует логический порядок ходов/позиций ответа. Trigger и будущие
  клиентские сообщения исключены, уже сохранённый ответ предыдущего хода включён.
  Scoped GET требует authorizationId/snapshotCursor, ограничивает cursors 4096
  символами и исходным deadline; pageSize 1–200/default 50. Обратные страницы
  возвращаются в прямом порядке; удалённые сообщения фильтруются при чтении.
- JSON budget 256 KiB уменьшает только число сообщений окна/страницы.
  Отдельный элемент и replace полей никогда не обрезаются. Невмещающийся блок
  закрывает dispatch с payload_too_large и штатной передачей сотруднику.
- Голос использует явно выбранный штатный STT, prepare/run/store и сохранённую
  стенограмму. Сервис получает text/wasVoice/messageId/duration, без аудио.
  Durable checkpoint исключает слепой повтор STT после сбоя. Недоступный STT
  или отсутствующая историческая стенограмма не заменяются фиктивным текстом.
- Contact сохраняет публичный Message.text без выдуманной vCard. HTTP-результат
  не принимает patch контакта/определений. После сотрудника новый snapshot
  не изменяется повтором старого callback.

UI и принятый baseline не менялись. Файлы/оформленные ответы, инициатива и UI
остаются объёмом других задач этапа; они не объявляются реализованными T-189.

## Штатный контур

Использованы существующие Compose, PostgreSQL и Redis основной копии.
Общие контейнеры не перезапускались и не пересоздавались. Аккаунты и конфигурация
не менялись, seed и отдельные HTTP-сервисы не запускались.

```powershell
docker compose -f compose.yaml -f compose.dev.yaml build backend-admin
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD init
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python manage.py check
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python manage.py makemigrations --check --dry-run
```

Init применил integrations.0036 и tenancy.0085. Check: 0 issues;
makemigrations: No changes detected. Настоящий backend на 8010 вернул
`database=true, redis=true` для `/api/v1/health/ready/`.
Readonly SQL основной БД: 4 организации, возможность внешнего исполнения
включена у 0, внешних подключений 0.

Windows source mount задержал первоначальный прогон до тестов; использован
документированный для T-188 canonical Compose из того же backend-образа без
source mount, с теми же dev DEBUG/CLOUD, PostgreSQL, Redis и секретами.
Тесты работают только в изолированной `test_chatballs`; `--create-db` применён
однократно при изменении схемы, далее только `--reuse-db`.

## Проверки

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_context_voice.py chatballs/ai/external_agents/test_context_budget.py chatballs/ai/external_agents/test_runtime_limits.py chatballs/ai/external_agents/test_runtime.py chatballs/ai/external_agents/test_runtime_control.py chatballs/ai/external_agents/test_send_guards.py --tb=short --show-capture=no
```

**29 passed**, 315.23s. STT, immutable HTTP retry, восстановление после STT
checkpoint, FIFO/callback/control, сообщения у лимита и send guards.

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/test_turn_pseudonymization.py chatballs/speech/test_routing.py chatballs/conversations/test_voice_ai_and_features.py chatballs/webchat/test_site_fields.py --tb=short --show-capture=no
```

**23 passed**, 68.88s. В старом тесте псевдонимизации исправлена только подготовка:
явно назначен штатный Demo-провайдер, необходимый действующему серверному допуску.
Продуктовая логика маскирования и все проверки утечки сохранены.

```powershell
docker compose -f compose.yaml run --rm --no-deps -e CHATBALLS_DEBUG=true -e CHATBALLS_DELIVERY_MODE=CLOUD backend-admin python -m pytest --reuse-db -x -q chatballs/ai/external_agents/test_custom_fields.py chatballs/ai/external_agents/test_context_versions.py chatballs/ai/external_agents/test_context_history.py chatballs/ai/external_agents/test_context_voice.py chatballs/ai/external_agents/test_context_budget.py chatballs/ai/external_agents/test_consent.py chatballs/ai/external_agents/test_contracts.py chatballs/ai/external_agents/test_runtime_concurrency.py chatballs/ai/test_site_context.py::CustomerDataPromptTests::test_hidden_deleted_builtin_and_unrelated_values_are_excluded chatballs/ai/test_site_context.py::CustomerDataPromptTests::test_mode_changed_after_turn_map_was_built_never_opens_the_value --tb=short --show-capture=no
```

**46 passed**, 525.48s. Все типы/состояния, source/field/contact/tenant isolation,
точные числа, native schema A→B→A, неизменный retry/новый ход, возвращение после
сотрудника, server consent, история/удаления/пагинация, STT и настоящие PostgreSQL
гонки/RLS. Всего три успешных набора покрывают **90 различных сценариев**
(voice/budget адресно повторены после изменений).

Последняя штатная сборка backend успешна, образ:
`sha256:cac83ad5e4c24a290b09bb14ac3450c8e3944410e6f06299d80bfb7ac0460150`.

OpenAPI проверен документированным verify_contract.py в отдельном Python venv:
openapi-spec-validator==0.9.0, PyYAML==6.0.3. **12 операций, 19 положительных,
16 отрицательных примеров, 10 векторов канонизации** — успешно. Зависимости
приложения ради этого валидатора не менялись.

Ruff затронутых файлов успешен. Изменённые модули меньше 300 строк;
разделены проекция, политика/generation, JSON, публичные сообщения и STT.
Предупреждения тестов: существующий deprecated CheckConstraint.check и отсутствие
collectstatic в dev-образе. Полный набор тестов не запускался.

## C4 и границы доказательства

Пакет `skaro-c4-386745b4-3643-4bc3-ab32-4b1964b15914` принят владельцем и применён
как revision 41. Узкие `code-external-agent-context-*` покрывают реализацию,
связи и ordered dynamics; broad component-external-agent и будущие представления
media/proactive/UI сохраняются planned. До проверенной публикации новые planned
элементы не объявляются current.

Результаты контролируемых вызовов внутри автоматических тестов не являются
работой приложения с реальным GoCoStack. Реальные внешние STT/LLM, мессенджеры,
публичные DNS/HTTPS и production-операции не выполнялись и по решению владельца
не входят в условия закрытия задачи.
