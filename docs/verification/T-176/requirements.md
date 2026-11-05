# Сверка SPEC-0037 R-1–R-31

Это карта доказательств и незакрытых проверок, не новая спецификация.
Старые отчёты обозначают результаты прежних задач, а не повторный прогон T-176.
Сведения о личной приёмке — из принятой SPEC-0037/ответов Skaro.
Для каждого требования сохраняется первоначальный объём; ограничения проверки
не переименовываются в исполненные требования.

| Требования | Доказательства | Что ещё не доказано в текущем контуре |
| --- | --- | --- |
| R-1 | [T-168](../../service-integrations-t168-verification.md): реальное подключение в прежней задаче; T-176: штатные настройки/каталог | Здесь ServiceConnectionSettings=0; полный путь подключения повторно не проверен |
| R-2 | Штатный compose, PostgreSQL/Redis readiness, backend и worker/worker-events; новые службы не добавлены | Нет нового инфраструктурного blocker |
| R-3, R-4, R-5 | [Контракт](../../service-adapter-contract.md); T-176 test_schema_registry: независимый probe, typed schema/handlers/extensions/версии; [T-168](../../service-integrations-t168-verification.md) | Независимый реальный внешний адаптер, операции/файлы и новый пользовательский сценарий в живом контуре не подтверждены |
| R-6 | [T-169](../../service-integrations-t169-verification.md), определения presets и копирование | Реальный пресет подключённого сервиса с исполнением не проверен |
| R-7 | [T-168](../../service-integrations-t168-verification.md): хранение/редакция/протоколы; новые SMTP/S3 входы и safe outputs в T-176 | Реальные OAuth/callback/обновление токена и внешний файловый путь остаются открытыми |
| R-8 | [T-169](../../service-integrations-t169-verification.md); T-176: форма своего сценария/список шагов без глобальных действий | Сохранение и исполнение полного нового смешанного сценария в текущем UI ещё не проверены |
| R-9, R-10 | Общие blocks/bindings в execution и [описание сценария](../../scenario-definitions.md); прежние адресные composition-проверки перечислены в [T-172](../../service-integrations-t172-verification.md) | Реальные ветви/ожидания/итерации с внешним сервисом не подтверждены; отложенные conversation.topic/метки контакта не объявлены готовыми |
| R-11 | [T-172](../../service-integrations-t172-verification.md): штатный API запуск/dedup/worker/журнал; [T-173](../../service-integrations-t173-verification.md): AI runtime | Все способы запуска на одном реальном внешнем сервисе здесь не проверены |
| R-12 | T-176: 301 executable actions; 367 базовых/775 полных inventory entries; полный resolver app/platform/socket; coverage=0 problems; классификация auth/transport/health/protocol | Каталог не является разрешением реального административного эффекта; такие эффекты на установке не выполнялись |
| R-13 | [T-172](../../service-integrations-t172-verification.md), EntityLink и synchronization services/tests | Реальный обмен, условная запись/конфликты и заполненные UI-состояния отсутствуют |
| R-14 | T-176 tests: tenant не получает globals, свежие user/token/session, отзыв прав, закрытый bootstrap; [T-173](../../service-integrations-t173-verification.md) и [T-174](../../service-integrations-t174-verification.md): grants/RLS | Реальные внешние действия всех инициаторов с отзывом доступа не проверены |
| R-15, R-16, R-17 | [T-173](../../service-integrations-t173-verification.md), [T-174 AI](../../service-integrations-t174-ai-verification.md): self/ask, digest, общий runtime, псевдонимизация | Полный реальный AI/service путь и наполненная карточка подтверждения требуют внешнего доступа; принятие ограничения владельцем не является внешним тестом агента |
| R-18, R-19, R-20 | [T-170](../../service-integrations-t170-verification.md), [T-175 merge](../T-175/main-merge.md): snapshots/leases/receipts; T-176: platform idempotency, storage probe conflict, update state | Реальное падение на границе внешнего эффекта/фиксации и сверка неизвестности ещё не подтверждены; глобальные I/O не объявляют автоматический retry |
| R-21 | Общие budgets/backoff/connection policy в execution; прежние проверки [T-170](../../service-integrations-t170-verification.md) | Реальные rate limits/Retry-After и независимость живых подключений не проверены |
| R-22 | [T-172](../../service-integrations-t172-verification.md): durable receipt/outbox, ранние callback, dedup/курсоры | Реальные подписанные внешние события/callback и cursor не проверены |
| R-23 | [T-170](../../service-integrations-t170-verification.md), общие control/recovery и composition-проверки [T-172](../../service-integrations-t172-verification.md) | Отмена уже отправленного внешнего запроса и реальная компенсация не подтверждены |
| R-24 | [T-170](../../service-integrations-t170-verification.md): 7/30, files, protected state; [T-175](../T-175/main-merge.md): safe receipt; T-176: отсутствие глобальных credentials в результатах | Полный живой внешний файловый/retention путь не повторён; unit-доказательства не заменяют его |
| R-25 | [T-172](../../service-integrations-t172-verification.md): штатный API Run и журнал; [T-173](../../service-integrations-t173-verification.md): инициатор/результат | Заполненный смешанный журнал всех состояний/восстановления здесь не проверен |
| R-26, R-27, R-28 | Личная приёмка обоих baseline 22.10.2026 прямо записана в принятой SPEC R-28; T-176 не добавляет UI | Приёмка макета не является проверкой всех состояний реализации; непросмотренные заполненные состояния остаются открытыми |
| R-29 | Миграций T-176 нет; default tenant API реестра сохраняет прежних потребителей; [T-173](../../service-integrations-t173-verification.md), [T-175 merge](../T-175/main-merge.md) содержат совместимость | Полного прогона нет и не требуется; фактические внешние HTTP/MCP доступы не подменялись |
| R-30 | [Журнал T-176](README.md): сборка, адресные тесты, browser, полный inventory, ru/en, NO GOD; probe только unit | Реальный независимый адаптер/сценарий, OAuth/callback/эффект/восстановление остаются blocker общей приёмки |
| R-31 | [Контракт](../../service-adapter-contract.md), [сценарии](../../scenarios.ru.md), [новые глобальные действия](../../native-global-actions.md) и текущие отчёты | Полная готовность функции/этапа не заявляется до выполнения всех требований и окончательного C4 review/submit_result |

Проверка в T-176 не реализует будущие брендовые CRM/Mindbox и не расширяет
возможности уже установленного брендового пакета. Неподдерживаемая им запись
или синхронизация не становится поддерживаемой от наличия общего runner.
