# T-178 — фактическая проверка

Дата: 04.11.2026. Проверки выполнены в собственном окружении задачи Skaro,
на копии штатных данных, через настоящие PostgreSQL, Redis и backend.
Mock API, подменный backend, временный HTTP-сервер, seed и смена доступов
не использовались. Полный набор тестов не запускался.

## Статус

Реализация находится в ветке задачи. Завершение и публикация не заявлены.
Владелец предоставил API-ключ SpeechKit и каталог. Подключение сохранено
через штатную защищённую форму (integration 23); ключ не записан в файлы.
Настоящая проверка STT v3 с короткой тишиной прошла: POST проверки integration
23 вернул 200/OK за 7389 мс (04.11.2026 19:04:32 UTC). Сохранённая модель
по умолчанию — general. Это проверка доступа, не качества диктовки.
Первая живая проверка выявила отказ локального tenant-guard, следующая —
отсутствующую зависимость httpx; исправлены контекст проверки прав и
requirements.txt. Настоящая минутная диктовка затем прошла в штатном виджете:
старт 04.11.2026 19:44:41 UTC, автоматическая остановка через 60 секунд,
HTTP 200, 638 символов распознанного текста. Текст/аудио этой записи не
сохранялись в отчёт. Тест декодирования ниже не подменяет живую проверку.
До предоставления доступа штатный `backend-admin / manage.py shell`
подтвердил отсутствие подключения SpeechKit. После сохранения через форму
проверены только его метаданные: integration 23, организация 1, UNCHECKED;
секрет не выводился. Сохранение вернуло HTTP 201, поле ключа очищено.

Личная приёмка полного voice-design предшествует продуктовому UI:
[OWNER-ACCEPTANCE.md](../../../design/baseline/widget-speech/OWNER-ACCEPTANCE.md),
принятые артефакты `781478ad5ddeaf8680eac33e6e80905dde8a6de8`.
Уточнение общей C4-модели принято владельцем и применено Skaro: пакет
`skaro-c4-df20aa86-1b06-49e8-acca-694278583ef2`, ревизия 14. Он фиксирует
уже полученную приёмку дизайна и общую границу consent, сохраняя planned
до проверенной публикации реализации.

## Выполненные проверки

Все команды запускались из корня репозитория. `docker compose` использует
имя/файлы окружения, назначенные Skaro. Backend-тесты — с `--reuse-db`.

| Команда / проверка | Результат |
| --- | --- |
| `docker compose exec -T backend-admin python -m pytest chatballs/webchat/test_consent.py chatballs/webchat/test_pre_chat.py chatballs/i18n/tests.py --reuse-db -q` | 20 passed, 1 skipped |
| `docker compose exec -T backend-admin python -m pytest chatballs/speech/test_routing.py chatballs/speech/test_formats.py chatballs/speech/test_results.py chatballs/webchat/test_dictation_guards.py chatballs/webchat/test_consent.py chatballs/conversations/test_voice_ai_and_features.py --reuse-db -q` | 23 passed |
| `docker compose exec -T backend-admin python -m pytest chatballs/ai/test_agent_cards.py chatballs/integrations/test_pre_chat.py chatballs/i18n/tests.py --reuse-db -q` | В объединённом запуске с voice round trip: 49 passed, 1 skipped; voice сначала выявил округление 4 секунд в 5 |
| `docker compose exec -T backend-admin python -m pytest chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_voice_message_round_trip --reuse-db -q` | После исправления округления: 1 passed |
| `docker compose exec -T backend-admin python -m pytest chatballs/webchat/test_recording_configuration.py chatballs_backend/test_speech_asgi.py --reuse-db -q` | 3 passed; тест миграции сначала выявил одинаковые названия тестовых подключений |
| `docker compose exec -T backend-admin python -m pytest chatballs/webchat/test_recording_configuration.py::WebRecordingMigrationTests::test_migration_preserves_voice_permissions_and_existing_configuration chatballs/ai/test_transcription_provider.py --reuse-db -q` | После исправления данных теста: 11 passed |
| `docker compose exec -T web-chat npm test -- src/speech/draft.test.ts src/preChatModel.test.ts src/widgetAppearance.test.tsx` | 14 passed |
| `docker compose exec -T web-chat npm test -- src/preChatModel.test.ts src/consentText.test.tsx` | 10 passed |
| `docker compose exec -T frontend npm test -- src/i18n/catalog.test.ts src/features/integrations/pre-chat/model.test.ts src/features/integrations/pre-chat/PreChatText.test.tsx` | 9 passed |
| `docker compose exec -T backend-admin python manage.py makemigrations --check --dry-run` | No changes detected |
| `docker compose exec -T backend-admin python -m pytest chatballs/integrations/test_check_permissions.py --reuse-db -q` | 1 passed за 107,45 с: настоящий runtime RLS, администратор 200, сотрудник 403, чужая интеграция 404; используется штатная локальная проверка DEMO, без сетевой заглушки |
| `docker compose exec -T backend-admin python -m pytest chatballs/conversations/test_transcribe_permissions.py --reuse-db -q` | 1 passed за 264,58 с: администратор получает готовую стенограмму, чужое сообщение 404 под runtime RLS. Первый запуск выявил отсутствие обязательного контакта в данных нового теста; данные исправлены, неуспешный запуск не засчитан |
| `docker compose exec -T web-chat npm run build` | Успешно: TypeScript и Vite |
| `docker compose exec -T frontend npm run build` | Успешно: TypeScript и Vite; штатное предупреждение о размере bundle |
| `docker build -f apps/backend/Dockerfile.production -t chatballs-backend-production:t-178-verify .` | Успешно; итоговый образ `22a34796a2941c2f2bbf688738078468ba84fa63d4995356830d749e163965bb` |
| Повторная сборка production backend после исправлений прав и зависимости httpx | exit 0, образ `763a5217d1e895cebcf84260d518e00d5205f5b18e6bb490290c06e70f49ef60` |
| Финальная сборка production backend с MessageTranscribeView и актуальными тестами | exit 0, образ `a3d27dc50ef18ca4025d6be573895442abac17664136b959d83fc5c29696870d`; CMD gunicorn / wsgi_app, FFmpeg входит в образ |
| `docker build -f deploy/docker/frontend.Dockerfile -t chatballs-frontend-production:t-178-verify .` | Успешно: npm ci, сборка обоих приложений, nginx; образ `d20cffd7682ea3348c6ac9986d235dd49ccde9af43651a3171ffdaedbde01f25` |
| Повторная сборка frontend-образа после мобильной CSS-правки | Итоговый образ `553763a42d6958de8674aa2241e80c2a400116643abbddd73c8c15c05b3922bb`; после восстановления Skaro команда повторена, exit 0, обе сборки npm подтверждены кешем Docker |
| Проверочный Dockerfile на основе собранного frontend-образа с единственной командой `RUN nginx -t` | Синтаксис nginx корректен; HTTP-сервер не запускался |
| `git diff --check` | Успешно; предупреждения Git о LF/CRLF |

Dev-образы собраны штатным `start_environment`; миграции применены штатным
запуском. После изменения исходников окружение повторно обновлялось Skaro.
Ранние ошибки сборки (Docker credential helper, зеркало apt и несовпадение
версии lucide с lockfile) устранены; это не считалось успешной проверкой.

FFmpeg-тесты действительно кодируют PCM в памяти и декодируют WebM/Opus,
Ogg/Opus и fragmented MP4/AAC. Декодированные 60 секунд принимаются,
61 секунда отклоняется; неверный контейнер/размер не передаются STT.
ASGI-тест подтверждает BytesIO для тела более стандартного порога spool
и отказ при превышении общего предела. Проверяется шифрование ключа в БД,
исключение SpeechKit из текстовых провайдеров, наследование совместимого STT,
отсутствие fallback при неисправном явном выборе, сохранение старых разрешений.

## Штатный браузер

Использован task-local Playwright и существующая демо-учётная запись.
Frontend обращается к backend задачи; через его proxy и напрямую получен
`/api/v1/health/ready/`: database=true, redis=true. В ходе холодного запуска
наблюдались временные PoolTimeout/500 и разрыв websocket; повторные запросы
и соединение восстановились. HTTP 200 одной страницы не принимался за readiness.

Проверены старый token/localStorage без серверного согласия, подтверждение
существующей сессии и сохранение подтверждения после reload. Проверены выбор
SpeechKit в штатной форме, отдельная карточка, скрытое поле ключа, ошибки
обязательных полей, блокировка проверки до сохранения. В WEB доступны три
режима микрофона; 61 секунда блокирует сохранение, 60 разрешены, default 10 МиБ.
Несохранённые настройки при этих проверках не применялись к подключению.

Снимки: [desktop](speechkit-desktop.png), [mobile](speechkit-mobile.png).
Они подтверждают только показанную форму, не запрос к SpeechKit.
В окончательной мобильной форме на ширине 390 px боковая панель скрыта,
карточка имеет x=20 px и ширину 350 px, горизонтального overflow нет.

С настоящим ключом выбран STT SpeechKit у существующего агента (id 1),
текстовый провайдер сохранён (id 1); пустая модель STT даёт general.
В WEB 5 включена диктовка 10 МиБ/60 сек. При частичном проверочном PATCH
случайно очистился список доменов; исходный единственный origin
http://127.0.0.1:15111 восстановлен сразу после обнаружения. Новые разрешения
и учётные данные не создавались. Виджет открыт через его настоящий frontend
с разрешённым referrer, без подменного сервера.

Реальный MediaRecorder с микрофоном Realtek: отказ разрешения сохраняет
текстовый ввод; после разрешения запись началась, таймер работал, отмена
сохранила черновик и не отправила запрос STT. Владелец затем надиктовал
60-секундную запись, остановленную автоматически. Пока ожидался ответ на
вопрос о готовности, Skaro остановил сервисы: перед записью readiness не была
повторно проверена, поэтому первая отправка получила сетевой отказ.
Запись осталась только в памяти виджета для повтора, правка черновика сохранилась.
Во время подъёма окружения была предпринята блокировка только Vite ping,
без изменения ответов продуктового API. Она не предотвратила dev-reload:
страница перезагрузилась, запись из памяти была потеряна. Восстановления записи
с диска нет, успешная транскрипция первой минутной попытки не заявляется.

После восстановления окружения Skaro readiness подтвердил database=true,
redis=true. Повторная проверка подключения 23 прошла: 200/OK за 7632 мс.
Короткая запись настоящего микрофона сначала получила таймаут; повтор той же
записи вернул 400/empty за 4661 мс. Это ожидаемая пустая речь без диктовки.
Черновик длиной 52 символа, включая правку во время ожидания, сохранён;
доступны повтор/отмена/обычный ввод. Заглушки и подмена API не использовались.
Для новой минутной попытки владелец повторно подтвердил готовность; Skaro
снова остановил окружение при ожидании ответа, поэтому перед записью повторно
запрошен штатный запуск и проверка readiness.

Новая минутная попытка прошла после подтверждённой readiness. Результат
добавлен к актуальному черновику: 691 символ, исходный текст и правка во время
распознавания сохранены. До обычной отправки shell-проверка сессии 21 показала
0 Conversation и 0 Message. Черновик можно очистить; 4001 символ остаётся
целиком, видна подсказка сокращения, отправка отключена. Для проверки обычной
отправки распознанный текст удалён и заменён несекретным проверочным текстом:
кнопка отправки вернула 201, созданы один диалог, текст клиента и ответ AI.
На ширине 390 px статус имеет x=12, width=366, горизонтального overflow нет.

Временно выбран штатный режим голосового сообщения. Настоящая короткая запись
сохранена как Message 148: voice, WebM, 2 секунды, transcript_status=FAILED;
диалог 32 — PAUSED/OPERATOR, в виджете «Ожидаем ответа сотрудника». У агента
явно выбран SpeechKit 23, тестовый override провайдера выключен. Запись доступна
для воспроизведения; начало следующей записи меняет «Пауза» на «Воспроизвести»,
после отмены композер снова доступен. При лимите 2000 байт/60 секунд диктовка
автоматически отправлена примерно через 1540 мс: размер достигнут раньше
времени; ответ empty, текущий черновик сохранён. Затем WEB восстановлен в режим
dictation с 10485760 байт/60 секундами полным PATCH текущей конфигурации.

Проверка ручного повтора расшифровки оператором выявила аналогичный RLS-дефект:
403 до STT при наличии capability. MessageTranscribeView теперь проверяет права
в короткой tenant_atomic; внешний вызов остаётся за пределами транзакции.

После окончательного штатного start_environment readiness через frontend
подтвердил database=true/redis=true, вход существующего демо-администратора —
200. Ручной повтор Message 148 прошёл проверку прав и вернул обработанный
таймаут STT (502 за 12017 мс), вместо прежнего 403. Исходный файл после этого
получен штатным API: 200, audio/webm, 6677 байт. Ошибка не удалила голосовое.

Клавиатура в штатном виджете: Enter на кнопке диктовки запускает настоящий
микрофон; Shift+Enter в поле добавляет перенос; Escape в поле отменяет запись.
За эту отменённую попытку — 0 запросов /dictation/, черновик с переносом
сохранён, микрофон снова доступен. Итоговый мобильный снимок проверен визуально:
[отмена диктовки](dictation-mobile-cancelled.png), 390×844, overflow отсутствует.

## Синхронизация с main — 05.11.2026

По указанию владельца выполнен git merge main (ffb1c505). Единственный Git-конфликт
в access.py разрешён сохранением session_available из T-178 и делегированием
_resolved_web_session общему session_access.resolved_web_session из main.
Проверки публикации/origin/активности и серверный consent сохранены.

Первый штатный запуск выявил две конечные миграции integrations: SpeechKit 0030
и native actions 0032. Добавлена 0033_merge_speech_and_native с обеими
зависимостями и пустым operations, без переименования применённых миграций.
Повторный start_environment успешно собрал/запустил штатный контур и применил
обе ветки и 0033. showmigrations integrations --plan отмечает их [X];
makemigrations --check --dry-run вернул No changes detected.

Повторно проверено только затронутое разрешением: consent, диктовочные guards,
WebSession в native widget calls, голосовое, origin и срок жизни сессии.
Результат: **16 passed за 73,77 с**, --reuse-db, без полного прогона.
Команда из корня репозитория:

```text
docker compose exec -T backend-admin python -m pytest chatballs/webchat/test_consent.py chatballs/webchat/test_dictation_guards.py chatballs/integrations/action_catalog/test_native_widget_calls.py chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_voice_message_round_trip chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_widget_origin_policy_is_scoped_per_widget chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_declared_host_origin_cannot_override_browser_origin chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_browser_origin_header_is_enough_without_declared_host_origin chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_idle_session_stops_being_accepted chatballs/webchat/tests.py::PublicWebChatWidgetTests::test_active_session_keeps_renewing_itself --reuse-db -q
```

Проверки сборок и настоящей минутной речи выше относятся к принятой реализации;
UI и STT-адаптер при разрешении конфликта не изменялись. access.py — 86 строк,
merge-миграция — 12; маркеров конфликта и ошибок diff --check в них нет.

## Итог и ограничения

Сборки, целевые тесты, настоящая минутная диктовка, первый достигнутый предел,
сохранность черновика и обычных голосовых проверены. Новые файлы меньше 300
строк; ChatComposer — 87, useDictation — 83, изменённый voice_views — 197,
integrations/views — 264. Прежние крупные каталоги i18n и webchat/tests.py
добавили только импорты/подключение словаря или проверку фактического аудио;
речевая логика вынесена в отдельные модули.

Сетевые таймауты и остановки контура действительно наблюдались и описаны выше;
они не выдаются за успешные попытки. Очередь SpeechKit может превышать локальное
ограниченное ожидание. Полный тестовый прогон и TTS не выполнялись. Итоговый C4
review хранится в Skaro и привязывается к changeHash после финального коммита;
публикацию результата Skaro подтверждает отдельно.

Обработка аудио поставщиком и неизвестный исход cleanup описаны в
[справке](../../speech.ru.md). TTS и UI событий сайта этой задачей не реализуются.
