# T-175: проверка слияния main

Дата: 2026-11-05. Владелец явно разрешил `merge main` и завершение задачи.
В ветку T-175 с HEAD `94259789` включён main `de2927a5`; публикацию выполняет Skaro.

## Разрешение конфликтов

- `test_catalog_coverage.py`: сохранено точное сравнение inventory с URL resolver
  и реестром вместо устаревшего фиксированного количества записей.
- `native_results.py`: совмещены идемпотентная запись receipt из main и сохранение
  failed-результата из T-175. Старый completed payload нормализуется для сравнения;
  другой digest/результат запрещён. Повтор не создаёт второй receipt или аудит.
- `feature_views.py`: тонкая HTTP-обёртка сохранена; синхронизация voiceMessages
  с режимом микрофона перенесена в общий `communication_settings.py`.
  Явная диктовка не переключается этим флагом.
- `views.py`: сохранены общие application services T-175 и отдельная транзакционная
  граница проверки SpeechKit из main. `management.checked` подготавливает запрос
  под RLS, выполняет I/O вне транзакции, затем повторно проверяет полномочия
  и runtime revision перед записью результата.

Закрытые TypeSpec обновлены под штатные payload из main: SpeechKit, возможности
распознавания, каталог Yandex Cloud, режим и ограничения записи, событие сайта,
язык распознавания агента. RU/EN подписи зарегистрированы в общих словарях.
Нового интерфейса или ветвления редактора по имени действия нет.
Inventory после слияния: 315 входов, 278 product-связей, 37 protocol-входов,
275 различных действий. Auth boundary остаётся отдельной описью.
Изменения main по речи и событиям сайта сохранены, включая первый ответ агента.

## Исполненные проверки

Окружение пересобрано и запущено через `start_environment` после изменения кода.
Только затронутые тесты, без полного прогона:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_merge_compatibility.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_failed_result.py chatballs/integrations/action_catalog/test_native_io.py chatballs/integrations/action_catalog/test_native_settings.py chatballs/integrations/action_catalog/test_native_connections.py chatballs/integrations/action_catalog/test_native_agents.py chatballs/integrations/action_catalog/test_native_widget_files.py chatballs/integrations/test_check_permissions.py chatballs/webchat/test_proactive.py::ProactiveTurnTests::test_one_real_domain_message_without_a_fictional_customer_or_second_model_cycle chatballs/webchat/test_proactive.py::ProactiveTurnTests::test_recovery_after_domain_commit_before_checkpoint_does_not_call_model_again chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short -x
```

Выполнено через `docker compose exec -T backend-admin`: **31 passed,
7 warnings, 567.00 s**, exit 0. Предупреждения: старый Django CheckConstraint
и отсутствующий каталог staticfiles в тестовом контейнере.
Новые проверки покрывают HTTP/native I/O boundary, отказ при смене revision,
секреты в результате/receipt, режим диктовки, совместимость повторных receipt.
Существующий тест агента проверяет roundtrip языка распознавания.
Два адресных proactive-теста подтверждают один доменный эффект и восстановление
без второго вызова модели. Внешний SpeechKit здесь проверяется на границе unit-теста;
это не заявление о живой проверке внешнего сервиса.

`docker compose exec -T frontend npm run build`: tsc и Vite, **4664 modules,
3m 40s, exit 0**. Обычное предупреждение о крупных chunks.
Предыдущие проверки групп действий остаются в соседних журналах; после слияния
они не выдаются за повторно выполненные полные прогоны.

## Штатный браузер

Task Playwright, frontend `http://localhost:20012`, backend задачи через штатный
proxy `backend-app:8000`. `/api/v1/health/ready/` через frontend вернул HTTP 200,
`database=true`, `redis=true`. Использован уже установленный demo ADMIN.
В общем редакторе проверены выбор Yandex SpeechKit, поле каталога и ограничения
записи, варианты микрофона и «Язык распознавания» с русским/английским/языком
организации. Значения «Диктовка» и «Английский» отображаются штатными контролами.

Снимки просмотрены: [подключение](main-merge-connection.png),
[агент](main-merge-agent.png). Боковая форма прокручивается, заголовок и нижняя
кнопка остаются на месте. Консоль: 0 errors, 1 warning.
Собственный несохранённый черновик закрыт через «Не сохранять»;
сценарий и подключения не запускались. Аккаунты, пароли и роли не менялись;
seed, fake backend и временные HTTP-серверы не использовались.

Архитектурная проверка и публикация подтверждаются отдельными ответами Skaro.
Этот журнал не переводит широкие planned-компоненты в current и не завершает весь этап.

## Второе обновление main: озвучивание

Во время проверки main продвинулся до `24223e4c` (T-179). Первое слияние
зафиксировано коммитом `68d1afae`; в рамках того же разрешения владельца
включено новое main. Три конфликта разрешены с сохранением обеих сторон:
`views.py` передаёт выбор STT/TTS общему `management.checked`, Vite поддерживает
и отключение watcher из main, и интервал 1000 мс из T-175; compose сохраняет
`VITE_DEV_WATCH` и `UV_THREADPOOL_SIZE`.

TypeSpec покрывает `synthesisIntegrationId`, `synthesisModel`, `synthesisVoice`,
`answerPlaybackEnabled`, `ttsCheck` и явный `capability=stt|tts` проверки подключения.
Все поля используют общие контролы и RU/EN. Новый visitor synthesis endpoint
классифицирован отдельно: это протокол ручного проигрывания с WebSession,
consent и revision, без постоянного файла или нового сообщения. Автоматический
синтез запрещён принятой границей T-179, описанной в `docs/speech.ru.md`.
Итоговая опись: **316 входов, 278 product-связей, 38 protocol, 275 действий**.

После повторного `start_environment` выполнено:

```sh
python -m pytest chatballs/integrations/action_catalog/test_native_merge_compatibility.py chatballs/integrations/action_catalog/test_catalog_coverage.py chatballs/integrations/action_catalog/test_native_connections.py chatballs/integrations/action_catalog/test_native_agents.py chatballs/integrations/test_check_permissions.py chatballs/ai/test_agent_synthesis.py::AgentSynthesisSettingsTests::test_tts_is_explicit_and_unrelated_patches_keep_its_selection chatballs/ai/test_agent_synthesis.py::AgentSynthesisSettingsTests::test_foreign_integration_and_unknown_voice_are_rejected chatballs/ai/test_agent_synthesis.py::AgentSynthesisSettingsTests::test_tts_check_failure_does_not_disable_working_stt chatballs/i18n/tests.py::CatalogTests --reuse-db -q --tb=short -x
```

**24 passed, 8 warnings, 214.42 s, exit 0**. Те же типы предупреждений,
что выше. HTTP/native проверка TTS вызывается явно, вне транзакции, не меняет
результат STT и не раскрывает ключ. Roundtrip агента сохраняет модель/голос;
обычные доменные проверки отклоняют чужое подключение и неизвестный голос.
Внешний синтез подменён только на unit-границе теста; живой доступ не заявляется.

Повторный `frontend npm run build`: **tsc/Vite, 4665 modules, 1m 43s, exit 0**.
Ruff и `git diff --check` прошли; максимум в изменённых этой итерацией Python
модулях — 134 строки. После перезапуска все требуемые сервисы работают,
backend-app/platform, PostgreSQL и Redis здоровы; readiness через frontend
снова HTTP 200 с database/redis=true.

Task Playwright проверил выбор «Распознавание речи»/«Озвучивание ответов»
и три поля озвучивания агента. Снимки просмотрены:
[проверка подключения](main-merge-synthesis-check.png),
[настройки агента](main-merge-synthesis-agent.png).
Консоль 0 errors, 1 warning; черновик закрыт без сохранения. Ограничения по
учётным данным и штатному окружению сохранены. При холодной загрузке страницы
был таймаут навигации, последующий snapshot подтвердил загруженное приложение;
все перечисленные действия выполнены после успешной readiness-проверки.
