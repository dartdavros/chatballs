# T-174 — исходные команды публичного ответа

Промежуточная часть задачи; перечисленные ниже адресные проверки пройдены.
Полная приёмка T-174 ещё не завершена.

Четыре действия messages.post/request_contact.post/voice.post/attachment.post
вызывают общие application services operator_reply, voice_send и attachment_send.
Исходные HTTP API вызывают их же; HTTP rendering отделён в reply_http.
claim вынесен в reply_claim_service, прежний HTTP wrapper сохранён для
совместимости. Нет вызова APIView/искусственного Request/HTTP к себе.

media_operation сохраняет исходные lock, tenant, PUBLIC_REPLY operation_id,
повтор по прежнему Message.external_id/actor/kind и source-транзакцию.
Проверки канала, voice flag, lifecycle, назначения, размера/типа/запрещённого
имени, незаполненных переменных и исходные аудит/история не заменяются.
Неуспешный исход media-команды сохраняет прежнюю семантику HTTP Response:
уже совершённый source claim может быть зафиксирован, сообщение при отказе
транспорта не создаётся. Native runner не держит свою root-транзакцию поверх I/O.

DeliveryObservation охватывает только одну native-команду через ContextVar;
общий исходный dispatch сообщает начало и boolean исход, не отправляя ничего
дополнительно и не сохраняя payload/секреты. On-commit отправка черновика
проходит прежнюю границу и наблюдается до выхода native-команды.
Результат различает published, transportAccepted и deliveryConfirmed=false.
Созданное текстовое сообщение при отказе транспорта не считается доставленным:
шаг unknown, marker запрещает слепой повтор. WEB использует прежний polling
transport; внешний SMTP/Telegram/MAX этим не объявляются проверенными.

Новые проверки используют штатные PostgreSQL/WEB/файловое хранилище и общий
runner в изолированной тестовой базе. Fault injection отказа в существующем
dispatch — только автоматическая отрицательная проверка, не mock API/подмена
штатного контура. Seed реального окружения/аккаунтов не выполняется.

Все 124 действия исходной таблицы зарегистрированы. Новая проверка problems()
без prefix должна подтвердить соответствие всех 125 продуктовых API-входов;
пройдена. Дополнительная транспортная инвентаризация, native-grants ИИ,
полные типы feedback отчёта и финальный C4 review остаются работой задачи.


## Выполненные проверки

Первый init выявил потерянный legacy re-export claim_for_reply из message_views;
он явно восстановлен (as claim_for_reply). Повторный start_environment прошёл,
миграции без изменений, backend готов. Frontend proxy readiness: HTTP 200,
database=true, redis=true. Чужие контуры и аккаунты не менялись.

27 адресных проверок: passed, 299.35 с. Включены 6 native runner-тестов,
4 coverage-теста (в том числе полное problems()==[]), 5 i18n-тестов и 12
проверок прежних API/идемпотентности/отложенной отправки черновика.

```sh
docker compose exec -T backend-admin python -m pytest chatballs/integrations/action_catalog/test_native_messages.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/i18n/tests.py::CatalogTests chatballs/conversations/tests.py::RequestContactApiTests chatballs/conversations/test_domain_event_sources.py::DomainEventSourceTests::test_http_first_reply_claim_and_retry chatballs/conversations/test_domain_event_sources.py::DomainEventSourceTests::test_web_file_and_voice_public_replies_are_retry_safe chatballs/conversations/test_attachments.py::AttachmentApiTests::test_operator_sends_file_and_claims_dialog chatballs/conversations/test_attachments.py::AttachmentApiTests::test_blocked_and_oversized_files_are_rejected chatballs/conversations/test_attachments.py::AttachmentApiTests::test_transport_failure_does_not_store_message chatballs/conversations/test_voice_messages.py::VoiceApiTests::test_operator_sends_voice_to_telegram chatballs/conversations/test_voice_messages.py::VoiceApiTests::test_voice_send_claims_dialog_like_text chatballs/ai/test_assistance_send.py::AssistanceSendTests::test_normal_send_records_source_message_operator_time_and_retry_is_one_message chatballs/ai/test_assistance_send.py::AssistanceSendTests::test_real_web_transport_is_deferred_until_commit_and_not_scheduled_on_retry --reuse-db -v --tb=short
```

Дополнительный native-тест готового черновика сначала не собрался из-за
неверного импорта ReplySuggestionSend в фикстуре; импорт исправлен на исходный
assistance_send_models. Повтор — 1 passed, 35.07 с. Проверены on-commit
WEB dispatch, неизменность original_text, исходная связь ReplySuggestionSend,
replay без повторной отправки и отказ повторно использовать уже отправленный
черновик. Новый тест теперь входит в test_native_messages.py (7 проверок).

Штатный редактор показал все четыре новых названия и схему голосового:
Номер диалога, Аудиофайл, Длительность в секундах. Снимок
`element-2026-11-04T21-20-18-579Z.png` визуально проверен. Панель 480/480,
документ 1280/1280; 0 console errors и 1 прежнее предупреждение при навигации.
Проверочный сценарий отброшен через «Не сохранять».

Ruff/NO GOD и diff --check пройдены. Нового layout нет. Полный набор тестов,
реальная внешняя доставка и RTC не заявляются пройденными.
