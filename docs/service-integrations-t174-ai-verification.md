# T-174: явный делегат действий ИИ

## Принятое решение

Пакет `skaro-c4-59265996-5fff-40b7-8b7c-996aa36b8e0f` лично принят владельцем
и применён Skaro; `get_c4_context` подтверждает revision 15, problems=[].
Новые native grants и разрешения сценариев с native-действиями сохраняют
активного OWNER/ADMIN, явно включившего режим. Чтение каталога, миграция и
сохранение прежнего режима не назначают делегата. Старые сервисные grants
сохраняют прежнее поведение.

## Реализация

`AgentActionGrant` допускает ровно одну цель: сервисную операцию, сценарий
или точный native key. Делегат связан с организацией ORM/DB guards; forced
RLS сохранён. Миграции `0032_native_agent_delegates` и
`0079_native_agent_delegate_guard` не содержат выдачи прав или заполнения строк.

`native_principal` сохраняет выбранного администратора и проверяет его текущее
состояние. Общая AI policy связывает grant/revision/configuration/control/mode
с immutable Run и повторно проверяет делегата перед эффектом, чтением состояния
и итоговым ответом. Точная цель native grant и исходные scope/capability/domain
checks не заменяются разрешением сценария. Используется прежний runner;
фиктивное подключение Integration и отдельный исполнитель не добавлены.

Исходные actor/author — реальный делегат. ContextVar ограничивает provenance
агент/делегат/Run/Step текущим вызовом, включая аудиты исходного сервиса.
Отдельный технический execution audit записывается вместе с receipt и не
повторяется при replay; бизнес-факты и доставка не дублируются. Журнал показывает
агента и администратора в существующей колонке автора, скрывая служебные поля.
Подтвердивший или отредактировавший ask-запрос не заменяет делегата.

## Проверка окружения и интерфейса

Штатный `start_environment` собрал текущие исходники и применил обе миграции.
Frontend http://localhost:20016 использует backend http://localhost:20014;
readiness через frontend — HTTP 200, database=true, redis=true.
`manage.py makemigrations --check --dry-run`: No changes detected.
`manage.py check`: 0 issues.

Сборка `docker compose exec -T frontend npm --workspace @chatballs/internal-ui run build`
прошла: tsc, Vite, 4643 модуля, 2м51с. Сохраняется предупреждение больших chunks.

Browser: существующий демо-аккаунт и существующий агент «Консультант»;
никаких seed/reset/новых учётных записей/изменений разрешений. Каталог API
возвращает 125 native-действий, существующая карточка отображает 125 строк
с прежними режимами и точным согласованным пояснением. Документ 1280/1280,
карточка 561/561. Скриншот `page-2026-11-04T23-36-09-776Z.png` визуально проверен.
Ни одна из 125 строк не имеет горизонтального переполнения; кнопка сохранения
остаётся disabled. Запросы каталога успешны. В сессии получен 409 email/options
для фонового демо-диалога, прежнее предупреждение WebSocket и ошибка его
повторного handshake; эти сообщения не скрыты под утверждением чистой консоли.

## Адресные backend-проверки

Первый прогон: **27 passed, 13 failed, 681.38 с**. Все 13 ошибок указывали
на одну причину: guard делегата ссылался на несуществующее стандартное имя
таблицы вместо исторического `identity_employeeprofile`. Миграция исправлена
на получение `_meta.db_table` из historical apps. Только эта новая миграция
переприменена в task environment и отдельной тестовой БД без пересоздания данных.
Прежние service-grants/runtime/approval/privacy/RLS и i18n прошли (27 проверок).

Команда первого прогона:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/execution/test_native_ai.py chatballs/integrations/execution/test_native_ai_policy.py chatballs/integrations/execution/test_native_ai_scenario.py chatballs/integrations/execution/test_ai_bridge.py chatballs/integrations/execution/test_ai_scenarios.py chatballs/integrations/execution/test_ai_runtime.py chatballs/i18n/tests.py::CatalogTests --reuse-db -v --tb=short
```

Адресный повтор после исправления: **20 passed, 215.41 с**. Подтверждены:
прямой self tool с восстановлением приватного входа, фактический автор внутреннего
комментария, ask/edit другим администратором без замены делегата, экспорт CSV
со строгим fileId/ownership, исходный и технический аудиты, их атомарный откат
и единственность после восстановления. Проверены блокировка/деактивация/смена
роли делегата, удаление binding, подмена exact key, отказ status/final reply,
межtenant DB guard/RLS, уникальная цель, отсутствие автоматического backfill,
смешанный service/native AI Run, unknown/reconcile I/O и весь coverage.
Сохраняются два прежних предупреждения Django/staticfiles.

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/execution/test_native_ai.py chatballs/integrations/execution/test_native_ai_policy.py chatballs/integrations/execution/test_native_ai_scenario.py chatballs/integrations/action_catalog/test_native_io.py chatballs/integrations/action_catalog/test_catalog_coverage.py --reuse-db -v -x --tb=short
```

Фактическое определение PostgreSQL trigger после переприменения проверено:
`enforce_tenant_fk('identity_employeeprofile', 'delegate_id')`. Контроль схемы
снова вернул No changes detected; readiness — HTTP 200 с database/redis.
Ruff, `git diff --check` и проверка размеров изменённых файлов проходят;
новых/расширенных Python/TS/TSX файлов длиннее 300 строк нет.

После переноса подписи источника в ru/en-словарь `CatalogTests` повторены:
**5 passed, 18.37 с**. Дополнительный mixed native/service автоматический Run
прошёл с исходным автором комментария и без второго эффекта; отзыв
ScenarioAutomation.delegate перед следующим Run запретил выполнение:
**1 passed, 45.09 с**.

```sh
docker compose exec -T backend-admin python -m pytest chatballs/i18n/tests.py::CatalogTests --reuse-db -v --tb=short
docker compose exec -T backend-admin python -m pytest chatballs/integrations/execution/test_native_automation.py --reuse-db -v -x --tb=short
```

Финальный `start_environment` выполнен на текущем коде. Browser повторно
подтвердил HTTP 200 каталога, 125 строк, переводимую подпись источника и точное
пояснение. Геометрия осталась 1280/1280 и 561/561. Разрешения не менялись,
несохранённых правок нет. Финальный скриншот
`page-2026-11-04T23-58-17-465Z.png` визуально проверен; 0 console errors,
1 прежнее WebSocket warning. После проверки браузер переведён на about:blank.

Тестовые сущности создаются исключительно в отдельной pytest БД. Внешний
адаптер смешанного сценария — существующий контрактный test adapter;
этот тест не объявляет реальное внешнее подключение проверенным. Остальные
проверки доменов, транспорта, файлов и общих контролов сохранены в соседних
`service-integrations-t174-*-verification.md`. Полного прогона проекта не было.
