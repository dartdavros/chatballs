# Глобальные действия общего каталога

`action_catalog/registry.py` хранит исполняемые дескрипторы вместе с `authority`.
Это граница существующего инициатора, не новая роль. Значение по умолчанию
`tenant` сохраняет поведение редактора, grants, preview и runner.
`native_action(key)` не разрешает глобальное действие. Для проверки inventory
служит `native_actions(authority=None)`; это не пользовательский API исполнения.

| Область | Действия | Источник полномочий |
| --- | --- | --- |
| instance | settings get/patch, email check, network get/patch, storage get/patch/check/migrate, update get/check/install | текущий активный HumanUser, прежние is_instance_admin/can_view_instance_settings |
| personal | profile update/appearance/language, avatar read/upload/delete, sessions read/revoke others, organizations options/create | текущий активный HumanUser; для сессий дополнительно живая собственная Django Session; создание организации проверяет прежнюю политику |
| platform | organizations provision | действующий PlatformToken, его активный PlatformOperator и прежняя capability |
| bootstrap | setup status/complete, packaged demo avatar read | прежний одноразовый мастер; complete запрещён после настройки |

`AuthorityContext` создаёт доверенный серверный код. Его нельзя получить из
определения сценария, ActionGrant или аргумента клиента. Он не создаёт tenant,
поддельный Request или временный Run. Перед действием права перечитываются
из БД: отозванный токен или заблокированный пользователь не сохраняют доступ
в ранее созданном контексте. Session-команды проверяют владельца, срок, auth
backend и authentication hash; чужая/пустая/отозванная сессия отвергается.

HTTP-обёртки и native-дескрипторы вызывают общие domain commands. Вызова APIView,
HTTP к собственному backend и универсальной записи таблиц нет. Логин,
password/TOTP, OAuth и выдача credentials остаются в существующем протоколе.
`setup.complete` не создаёт сессию как результат native-действия: вход владельца
остаётся частью исходного HTTP-мастера. Файловые операции используют переданные
доверенным вызывающим кодом `open_file`/`store_file`, ограничение размера и
штатные avatar/file services. В tenant-файл глобальный профиль не преобразуется.

## Подтверждения и восстановление

Каталог не является разрешением обновить установку, отправить проверочное письмо,
перенести файлы, отозвать сессии или создать организацию. Существующие формы,
подтверждения, аудит и отдельная процедура platform API сохраняются.
Глобальные эффекты не проходят через tenant-runner и не получают его receipt.
I/O-действия не объявляют безопасный автоматический повтор: `retry=NONE`.
После потери ответа нужно читать штатный статус и следовать процедуре операции.

Provisioning сохраняет прежний Idempotency-Key и конфликт другого payload.
Обновление установки сохраняет штатный файловый протокол updater; команда
сериализуется блокировкой UpdateState. Миграция хранения проверяет состояние
под блокировкой строки и пишет запрос в штатный outbox. S3 probe выполняется
вне транзакции; после него повторно проверяются права и версия конфигурации,
поэтому параллельная настройка не затирается. Счётчики переноса не переписываются
патчем настроек. Эти меры не обещают exactly-once внешнему провайдеру.

Ответы каталога не раскрывают SMTP/S3 credentials, masked access key и сырые
ошибки провайдера/updater. Пароль initial setup помечен secret. Пустой SMTP
пароль сохраняет прежнее значение по существующему контракту.

## Проверяемые примеры

Только для доверенного серверного кода, после штатной аутентификации:

```python
from chatballs.integrations.action_catalog.authority import AuthorityContext
from chatballs.integrations.action_catalog.registry import native_action

context = AuthorityContext("instance", user=authenticated_user)
descriptor = native_action("instance.settings.get", authority="instance")
result = descriptor.execute(context, {})  # повторная проверка текущих прав
assert native_action("instance.settings.get") is None  # tenant не получает действие
```

Для platform API повтор с тем же Idempotency-Key и тем же телом возвращает
ранее созданную организацию; другой payload должен быть отклонён. Исполняемый
пример на изолированной PostgreSQL test DB — `test_global_authority.py`.
Там же проверяются отзыв токена, чужая сессия, сохранение текущей сессии при
отзыве остальных и закрытый bootstrap. Настройки/ошибки хранения и конкурентный
probe проверяет `test_native_installation.py`. Это не живые внешние проверки.

## Полная опись API

`coverage.py` сравнивает все маршруты app/platform и socket-протоколы с
`*_inventory.json`, без whitelist префиксов. Каждая запись содержит точные
surface/route/method/handler, classification, evidence и либо действие с его
authority, либо конкретное объяснение отдельного протокола.
Классификации: product, credential_protocol, transport, health, protocol.
Бизнес-операция не исключается из-за слова auth или глобальных полномочий.
`chatballs_backend/urls_admin.py` монтирует только служебный Django admin
на отдельной административной поверхности. Его модельные CRUD-формы не являются
публичным продуктовым API app/platform и не превращаются в универсальные
действия сценариев. Этот scope не скрывает ни одного маршрута urls_app/platform.

`http_coverage.py` выводит только доказанные framework HEAD/OPTIONS из уже
описанного маршрута. Переопределённый HEAD/OPTIONS требует отдельной записи.
Новый префикс, лишняя/пропущенная запись, отсутствующий код, неизвестное действие
или несовпадающий API reference приводят к ошибке coverage. Проверка:

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_auth_boundary.py chatballs/integrations/action_catalog/test_http_coverage.py --reuse-db -q
```

Общий механизм и конкретные брендовые адаптеры имеют отдельную готовность.
Схемы, unit-тесты и полный inventory не доказывают реальный внешний обмен,
OAuth, восстановление внешнего эффекта или полное выполнение SPEC-0037.
