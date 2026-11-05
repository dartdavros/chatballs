# T-179 — реализация и проверка прослушивания

Проверки выполнены 05.11.2026 в копии задачи. Приёмку и публикацию определяет receipt Skaro; журнал сам по себе их не подтверждает.

## Контур и дизайн

Штатный Compose-проект skaro-chatballs-t-179 запускается только Skaro. Документированный gateway: http://localhost:20018; frontend:20004, backend:20002, platform:20003, web-chat:20005. Для DB-тестов подключён предусмотренный backend-admin без host-порта. Проверены database=true и redis=true. Миграция ai.0031 применена, Django check и makemigrations --check --dry-run успешны. Seed, изменение аккаунтов, паролей, ролей и доступов не выполнялись.

Источник UI — лично принятый design/baseline/widget-speech, OWNER-ACCEPTANCE.md, коммит 781478ad5ddeaf8680eac33e6e80905dde8a6de8. Использованы существующие поля, переключатель, статусы, общий спиннер и структура плеера.

Vite на Windows задерживал чтение bind mount (p9_client_rpc). Проверка выполнена через существующий nginx gateway и VITE_DEV_WATCH=0 только в запуске задачи. Холодная загрузка модулей по-прежнему занимает несколько минут; проверена фактическая загрузка интерфейса, а не только receipt запуска. Обычный default остаётся 1, polling 300 ms сохранён. После правок требуются start_environment и reload. В обоих nginx-конфигах synthesis отключает disk buffering и допускает 190 s ожидания ограниченного 180 s синтеза. Обходные HTTP-серверы не создавались.

## Сборки и тесты

Команды выполняются в корне task worktree с переменными окружения Skaro; Docker CLI должен быть в PATH. Полный набор тестов не запускался.

```text
docker compose exec -T frontend npm --workspace @chatballs/internal-ui run build
docker compose exec -T web-chat npm --workspace @chatballs/web-chat run build
docker build -f deploy/docker/frontend.Dockerfile -t chatballs-frontend-tts-check:t179 .
docker build -f apps/backend/Dockerfile.production -t chatballs-backend-tts-check:t179 .
```

Dev-сборки обоих приложений и production-образы успешны. Production frontend собирает оба приложения с npm ci; backend выполняет collectstatic. Отдельные validation builds с --network none подтвердили nginx -t production-образа и импорт YandexTTS/загрузку профилей langdetect backend-образа. Существующее предупреждение Vite о размере чанка не мешает сборке.

```text
docker compose exec -T backend-admin python -m pytest chatballs/webchat/test_synthesis_guards.py chatballs/speech/test_synthesis.py chatballs/speech/test_routing.py chatballs/webchat/test_consent.py chatballs/webchat/test_recording_configuration.py chatballs/ai/test_agent_cards.py::AgentCardUpdateTests::test_updates_instructions_without_touching_channel chatballs/ai/test_agent_cards.py::AgentCardActivationTests::test_transcription_integration_is_chosen_separately chatballs/ai/test_agent_synthesis.py chatballs/i18n/tests.py::CatalogTests --reuse-db -q
docker compose exec -T web-chat npm --workspace @chatballs/web-chat test -- src/speech/playbackCache.test.ts src/speech/audioFocus.test.ts src/speech/draft.test.ts src/consentText.test.tsx
docker compose exec -T frontend npm --workspace @chatballs/internal-ui test -- src/i18n/catalog.test.ts
```

Backend-сценарии пройдены несколькими целевыми запусками, не единым полным прогоном команды выше. В первых запусках исправлены две ошибки подготовки тестовых данных; исправленные сценарии повторно пройдены. Последний запуск всего test_synthesis_guards.py: 9 passed. Проверены успешная выдача WAV из сохранённого plain text без изменения истории, запрет выдачи после смены согласия/голоса во время внешнего запроса, origin, публикация, сессия, pre-chat, организация, контакт/подключение, аудитория и окончательность ответа.

После исправления версии согласия test_synthesis.py + test_consent.py: 8 passed; затем 4 теста синтеза повторены после ограничения моделей general. Пройдены агентские API-тесты независимой настройки/отключения TTS и сохранения STT-статуса при сбое TTS, routing, WEB-настройки и backend i18n. Frontend: 11 passed в четырёх файлах; internal-ui i18n: 3 passed.

Проверены single-flight, ключ session/message/text/revision, повтор, abort/revoke URL, отменённый поздний результат, повтор после ошибки, остановка аудио при записи и сохранение черновика. Reset/session/unmount используют тот же clear с abort/revoke; вызовы проверены в hook/session. Ruff по изменённым Python-файлам успешен. Проверены diff и размеры: изменённый код не превышает 300 строк, новые компоненты меньше 180 строк. Строки UI находятся в ru/en; секреты в файлы не записывались.

## Настоящие подключения и длинный ответ

Ключи владельца сохранены через штатные формы только в копии задачи. Значения ключей, payload и полные TTS-тексты в журнал не включены. SpeechKit (23) выбран отдельно: general/alena. Для нескольких ответов выбран OpenRouter (24), openai/gpt-4.1-mini; проверка подключения успешна. STT не включён вслед за TTS. WEB-прослушивание включено явно; прежние allowedOrigins и voice_message сохранены. Согласие предупреждает о персональных значениях текста.

Через настоящий API создан обычный навык с шаблоном заголовка/абзацев без примеров готового ответа. Ответы получены обычной перепиской настоящего LLM по существующим знаниям; Message через БД не создавались. Временное расширение тона агента восстановлено на исходное.

| Сохранённый AI-ответ | Текст | Реальный SpeechKit WAV | Длительность |
| --- | --- | --- | --- |
| 151, обычный | 2715 символов | 9 698 092 байта, HTTP 200 | 219,910385 s |
| 153, оформленный | 2717 символов | 9 702 700 байт, HTTP 200 | 220,014875 s |

Read-only проверка Message 153 подтвердила formatVersion=1, HTML-представление, окончательный отправленный AI-ответ и отсутствие HTML-тегов в plain text. Части: 994 + 998 + 725; точное соединение равно исходному тексту. Аудио воспроизводилось нативным Audio; повтор первого длинного ответа использовал тот же object URL без второго synthesis-запроса. До нажатия синтеза не было. TTS Message не создаёт.

## Браузерные сценарии

Task-local Playwright, настоящий backend и SpeechKit:

- Короткие ответы 147/149: HTTP 200; первый прослушан до ended (7 s). Pause/resume/repeat/stop используют тот же звук; переключение ответа оставляет один плеер. Текст и ввод доступны.
- Начало записи останавливает даже ожидающий звук до запроса микрофона. Отказ браузера в микрофоне показывает штатную ошибку; ввод доступен. Успешная запись этим сценарием не заявляется.
- Явная смена alena на john останавливает звук и очищает кэш; русский ответ получает ошибку языка без подстановки. Черновик сохраняется. Возврат alena позволяет новый реальный синтез.
- WEB off меняет согласие v3→v4 и закрывает плеер. После on v4→v5 старое подтверждение получает 400; UI обновляет disclosure. Только явное подтверждение новой версии открывает ввод и прежнюю историю.
- Быстрый stop/reopen во время loading объединяет запросы: один синтез и один object URL. Наблюдались настоящие create/revoke (1/0→1/1 при пустом голосе), после отключения ноль плееров/кнопок. Нативные функции только наблюдались, звук не подменялся. Голос восстановлен.
- На 390×844 playing/paused/error занимают одинаковые 82 px без горизонтального переполнения. На 320 px проверены английские Listen/Pause/Resume/Stop, продолжение/остановка клавишей Enter. Язык организации восстановлен на ru.
- На финальном коде длинная карточка повторно получила настоящий WAV (HTTP 200, 9 694 508 байт, 219,829116 s; небольшая вариация синтеза поставщика). Раскрытый плеер прокручивается в видимую область: низ 760 px, начало ввода 769 px. Loading/playing/paused/error сохраняют 82 px. Исправленный снимок просмотрен.
- Для отрицательной проверки проигрывателю назначен недоступный blob URL: нативная ошибка показана у ответа, черновик/ввод сохранены. Повтор снова воспроизвёл настоящий кэшированный WAV; synthesis-запросов осталось 1, URL создан 1. Это намеренный сбой media source, не подмена успешного Audio.
- Отключение всей сети перезагружало dev-клиент Vite и не засчитывается как проверка ошибки TTS. Вместо этого только один synthesis-запрос намеренно прерван Playwright через route.abort(internetdisconnected), без подстановки ответа. Запрос 1566 получил ERR_INTERNET_DISCONNECTED, UI показал ошибку с повтором и сохранил ввод/черновик. Повтор 1574 дошёл до настоящего backend/SpeechKit, получил 200 и воспроизводился. История осталась из сообщений 150–153, state=ai, thinking=false.
- Перезагрузка освободила старый blob URL (запрос к нему отклонён браузером), плеер не запустился автоматически. В отдельном настоящем посетителе создан короткий AI-ответ 155 (61 символ, реальный WAV 5,3361 s). Read-only проверка подтвердила, что новая переписка 34 содержит только сообщения 154/155. После её удаления штатным API (204) poll reset остановил звук: created=1/revoked=1, src пуст, плееров/кнопок 0; черновик сохранён, ввод доступен. Длинная проверочная история не удалялась.
- В финальной форме SpeechKit нажата отдельная «Проверить озвучивание»: TTS стал «Доступно», STT остался «Не проверено», ошибки отсутствуют. Обе строки до/после проверки имеют 55 px на desktop. Проверены тёмная тема и mobile 390 px: переполнения нет, строки 91 px. Исходная светлая тема восстановлена. У агента видны независимые SpeechKit/general/alena и человекочитаемый язык голоса. Секретное поле пусто и показывает маску сохранённого ключа.

Снимки: playback-mobile.png, playback-language-error.png, playback-en-320.png, agent-speech-settings.png, playback-formatted-mobile.png, speech-connection-dark.png, speech-connection-mobile-dark.png. Снимки проверены визуально и не заменяют сетевые/поведенческие проверки. На финальном интерфейсе настроек ошибок консоли нет; при загрузке виджета есть существующий favicon 404, при отрицательных сценариях — ожидаемые media/network errors.

Mock API, fake backend, временные HTTP-серверы, seed и изменения доступов не применялись. Другие окружения не изменялись.

## Слияние main de2927a — 05.11.2026

После проверки всех семи критериев Skaro потребовал разрешить конфликты интеграции с опубликованной T-181. В ветку задачи влита main de2927a. Пять конфликтов в App/ChatBody/api/useChatSession/useWidgetConsent разрешены совместным сохранением playback и siteEvent, обновления текста/версии согласия и invalidateConsent, а также checked/consentReady из main. Обычная отправка сохраняет отмену site-event из main; polling обрабатывает оба поля. Новые экраны или состояния не добавлялись.

Повторный start_environment завершён; gateway:20018 readiness вернул 200 с database=true/redis=true. Повторены только затронутые проверки:

```text
docker compose exec -T backend-admin python -m pytest chatballs/webchat/test_consent.py chatballs/webchat/test_synthesis_guards.py chatballs/webchat/test_site_events.py::SiteEventIngressTests::test_no_consent_no_receipt_or_conversation_and_form_revision_is_current chatballs/webchat/test_site_events.py::SiteEventIngressTests::test_new_required_form_cannot_be_bypassed_by_an_existing_token chatballs/webchat/test_proactive_status.py --reuse-db -q
docker compose exec -T web-chat npm --workspace @chatballs/web-chat test -- src/speech/playbackCache.test.ts src/speech/audioFocus.test.ts src/consentText.test.tsx src/proactivity/memory.test.ts src/participantAuthorship.test.tsx
docker build -f deploy/docker/frontend.Dockerfile -t chatballs-frontend-tts-check:t179 .
```

Backend: 18 passed за 82,07 s; frontend: 15 passed в пяти файлах. Production frontend собрал оба приложения с tsc/Vite (4465/3372 модуля), образ 2b10429607d7; осталось прежнее предупреждение о размере чанков. Полный набор тестов не запускался. Пять разрешённых файлов меньше 300 строк, useChatSession — 193 строки.

Штатная браузерная переписка после слияния создала 156/157; AI-ответ 157 содержит 61 символ. До нажатия синтеза нет. Реальный SpeechKit вернул WAV 236902 байта, native Audio 5,37093 s. Stop/reopen/pause использовали один запрос/URL, один плеер высотой 82 px, без overflow на 390×844. При WEB off согласие v5→v6 закрыло плеер, paused=true/src empty/created1 revoked1. При WEB on v6→v7 старая форма получила 400 и обновила disclosure, ввод оставался закрытым. Повторное явное подтверждение получило 200, вернуло прежнюю историю и черновик. Следующее нажатие выполнило новый успешный реальный синтез (5,39415 s), created2/revoked1, один плеер. AllowedOrigins и voice_message сохранены, playback включён обратно. Снимок playback-after-main.png просмотрен.

Прямое открытие iframe с разрешённым referrer даёт ожидаемые предупреждения postMessage о несовпадающем origin верхнего окна (useSiteFields/useSiteEvents); embedding-связь этим сценарием не проверялась. Ошибки этой проверки: существующий favicon404 и ожидаемый consent400. Успех не подменялся ответами, доступы не расширялись; использован штатный вход существующего демо-администратора без seed/reset.
