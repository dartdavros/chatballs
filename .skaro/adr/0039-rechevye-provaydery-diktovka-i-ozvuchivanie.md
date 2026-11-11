---
id: "0039"
title: "Речевые способности, диктовка и прямой SpeechKit"
status: accepted
date: 2026-11-03
---

## Контекст

STT сейчас вызывается из conversations/transcription.py через ai/provider/{factory,routing}.py; модели/ключи принадлежат агенту/интеграции. Микрофон web-chat/useVoiceRecorder.ts отправляет голосовое, лимит задан conversations/voice_views.py. У интеграции нет самостоятельного речевого вида. Нужны STT до Message и TTS сохранённого ответа.

## Решение

1. Новый модуль chatballs/speech отделяет contracts/routing/errors/formats и адаптеры от LLMProvider. Integration получает вид SPEECH_PROVIDER и YANDEX_SPEECHKIT; прежние совместимые STT переиспользуются через bridge. Ключ шифруется прежним механизмом, tenant/RLS сохраняются. SpeechKit не реализует chat/embeddings.
2. Выбор STT сохраняется у агента; модель по умолчанию определяется адаптером. TTS отдельно хранит интеграцию, модель при наличии и голос; пусто означает выключено. WEB задаёт off/voice_message/dictation, maxRecordingBytes, maxDictationSeconds и прослушивание. Новые функции выключены, прежние значения миграцией не расширяются.
3. Новый публичный webchat-вход диктовки проверяет origin/session/consent/режим/лимиты, вызывает speech вне DB-транзакции и возвращает текст. Нет ingest/Message/Conversation/AI из диктовки. Общий сервис consent сохраняет версию и время принятия WebSession после проверки формы; его переиспользует SPEC-0040. Старые сессии не объявляются согласившимися задним числом.
4. STT SpeechKit — REST API v3 RecognizeFile с inline content и ограниченным получением результата; обязательного бакета нет. REST v1 30 секунд/1 МБ не покрывает 60 секунд/10 МиБ. По завершении выполняется штатная попытка удаления внешнего результата DeleteRecognition; неизвестный исход не объявляется удалением.
5. WebM/Ogg/MP4 нормализуются выделенным FFmpeg-модулем через ограниченные pipes, без shell и постоянных временных файлов; фактическая длительность проверяется после декодирования. FFmpeg добавляется в существующие dev/production backend-образы, отдельная служба/ручная настройка хоста/env-файл не нужны.
6. TTS backend принимает ID доступного окончательного AI-ответа, сам читает сохранённый plain text и синтезирует только по нажатию. Длинный ответ обрабатывается частями без потери текста. Звук кэшируется в памяти виджета по session/message/text/config revision, очищается при reset/unmount; постоянного кэша/аудио-Message нет.
7. STT получает исходное аудио, TTS — окончательный текст с возможными персональными значениями. Это отдельный речевой получатель, описанный в настройке и согласии; псевдонимизация текстовой LLM сохраняется. Речевые payload/ключи не пишутся в логи. Нельзя обещать отсутствие хранения у поставщика из отсутствия локальных файлов.
8. Новый UI — только после личной приёмки baseline. Проверки включают реальный SpeechKit в штатном приложении; недоступность ключа не обходится mock API/seed.

## Варианты и последствия

Browser Speech API не обеспечивает выбранного организацией провайдера; SpeechKit как LLM смешивает способности; REST v1 не покрывает принятые лимиты. Поэтому выбраны отдельный capability-контракт и API v3. Речевые запросы оплачиваются организацией напрямую, тарифный слой не добавляется. Архитектура остаётся модульным монолитом со штатными PostgreSQL/Redis/worker; новая зависимость образа — FFmpeg. Planned не становится current от принятия документов.

## Основания

SPEC-0039, ADR-0029/0031; apps/backend/chatballs/ai/agent_models.py; apps/backend/chatballs/integrations/models.py; apps/backend/chatballs/webchat/sessions.py; apps/backend/Dockerfile и Dockerfile.production.

Официальные API: [режимы STT](https://aistudio.yandex.ru/ru/docs/speechkit/stt/), [REST v3 inline content](https://aistudio.yandex.ru/ru/docs/speechkit/stt-v3/api-ref/AsyncRecognizer/recognizeFile), [GetRecognition/DeleteRecognition](https://github.com/yandex-cloud/cloudapi/blob/master/yandex/cloud/ai/stt/v3/stt_service.proto), [форматы](https://aistudio.yandex.ru/ru/docs/speechkit/formats), [TTS](https://aistudio.yandex.ru/ru/docs/speechkit/tts/). Проверены 03.11.2026.

## Уточнение границ и дизайн-gate 04.11.2026

Личная приёмка полного baseline зафиксирована 04.11.2026: design/baseline/widget-speech/OWNER-ACCEPTANCE.md, принятые артефакты коммита 781478ad5ddeaf8680eac33e6e80905dde8a6de8, решение владельца «Я все проверил, закрывай задачу» (command_id 455a85e5-94c6-497e-919e-6931a8f54da3). Q-WIDGET-SPEECH-DESIGN закрыт этим отдельным решением; повторная приёмка макетов не требуется. Это не подтверждает реализацию, публикацию или живую проверку SpeechKit.

Общему code-web-consent принадлежат webchat/consent.py, consent_views.py и браузерные useWidgetConsent.ts/consentApi.ts. SPEC-0040 использует общий guard по rel-site-consent; собственный UI приглашения, TTL и первый контакт остаются planned под отдельным дизайн-gate. Диктовка использует ограниченную память на всех слоях входа: nginx без request buffering, ASGI BytesIO с верхним пределом, memory upload handler, затем FFmpeg pipes. Это конкретизирует принятое отсутствие постоянных временных файлов; новая служба, бакет или продуктовый сценарий не вводятся.
