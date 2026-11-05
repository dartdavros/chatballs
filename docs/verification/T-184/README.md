# T-184 — бессрочные WEB-запросы оценки

Дата проверки: 05.11.2026. Принятый пакет:
`skaro-c4-358626c8-fcc5-4d68-aa19-9f992e546180`, C4 revision 25.

## Изменение

Новые WEB-запросы хранят и возвращают `expiresAt: null`. Исторические даты
сохраняются, но не ограничивают WEB-credential. Миграция 0003 обновляет constraint,
оба SQL guard и security-barrier directory без изменения строк данных, прав,
владельцев объектов, RLS или ранее применённых миграций. Транспорт берётся из
неизменяемого факта завершения; другие каналы и сроки WebSession сохраняются.

Клиент использует nullable-контракт. Существующее состояние недоступности
называется `unavailable`; тексты, иконки, оформление и структура baseline
W2/R1–R6 сохранены. Время не переводит карточку или форму в это состояние.

## Воспроизводимые проверки

После штатного `start_environment`:

```powershell
docker compose exec -T backend-admin python manage.py check
docker compose exec -T backend-admin python manage.py makemigrations --check --dry-run
docker compose exec -T web-chat npm run build
docker compose exec -T web-chat npm run test -- src/ratings/lifecycle.test.tsx
docker compose exec -T backend-admin pytest -q --reuse-db --tb=short chatballs/ratings/test_no_expiry.py chatballs/ratings/test_expiry_migration.py chatballs/ratings/test_public.py chatballs/ratings/test_storage.py chatballs/ratings/test_concurrency.py chatballs/ratings/test_ui_contract.py chatballs/ratings/test_results.py chatballs/ratings/test_delivery.py::RatingDeliveryTests::test_actual_close_and_worker_poll_are_idempotent_with_delay chatballs/ratings/test_delivery.py::RatingDeliveryTests::test_disabling_and_deleting_cancel_pending_delivery chatballs/ratings/test_delivery.py::RatingDeliveryTests::test_unavailable_or_unsupported_delivery_does_not_send chatballs/ratings/test_delivery.py::RatingDeliveryTests::test_session_binding_never_returns_another_widget_or_customer_request
```

Итоговый backend-прогон: **35 passed** (214.87 с), `--reuse-db`, без полного набора.
Сборка web-chat и два клиентских теста прошли. Django check — без замечаний,
makemigrations — No changes detected. Изменённые Python-файлы прошли ruff.
Полный набор тестов не запускался.

`test_no_expiry` проверяет WEB-запросы возрастом 365 дней с NULL и прежней датой
истечения: poll, публичный API, runtime-роль, directory, SQL-вставку, повтор,
конфликт, отмену, удаление, организацию, старый verifier при смене секрета,
сохранение ограничений других каналов и срока сессии.
`test_expiry_migration` устанавливает старые guards только в транзакции Django
test database и применяет настоящие операции новой миграции. Проверяется точное
равенство всех строк запросов/результатов/настроек/outbox/аккаунтов/членств/сессий
и ACL/владельца directory до и после; старые credential и отмены сохраняются.

## Browser-проверка

Task-local Playwright MCP, реальный backend и БД/Redis окружения
`skaro-chatballs-t-184`. Адреса: frontend `http://localhost:20010`, backend
`http://localhost:20008`, web-chat `http://localhost:20011`.
Vite proxy направлен на `backend-app:8000` этого же Compose-проекта.
Демо-набор уже установлен; использована существующая ADMIN-учётная запись из
штатного манифеста. Seed, заглушки, временные серверы, изменение аккаунтов,
паролей, ролей или origin allowlist не применялись.

В копии данных не было запросов оценки. Настройки включены через штатный API
с серверными defaults и нулевой задержкой. Опубликованный виджет открыт с его
уже разрешённым Referer через Playwright navigation; его allowlist сохранён.
Создана обычная WEB-сессия, отправлено сообщение, диалог 32 закрыт API сотрудника.
Poller доставил один запрос с NULL expiry; карточка появилась в виджете.
Звезда открыла настоящую форму через sessionStorage, `opener === null`, credential
отсутствовал в URL. GET вопроса — 200 с `expiresAt: null`.

Часы браузера формы переведены на восемь дней вперёд без изменения времени
backend/БД: кнопка оставалась доступна, отправка — 201. Перезагрузка сохранила
результат и показала «Вы уже оценили этот разговор». Вторая заранее открытая
форма отправила другое значение: 409, затем GET 200 и исходная оценка 5.
Серверный возраст 365 дней проверяется backend-тестами, а не этим изменением
часов браузера. Форма без handoff показала существующее локализованное объяснение
недоступности. Горизонтального переполнения нет.

Повтор исходной отправки вернул 200 с прежним `receivedAt`; в БД остались одна
оценка и одно событие `ratings.received`.
Скриншоты: [результат после перезагрузки](rated-reload.png),
[недоступный запрос](unavailable.png). Изменённые исходные файлы — не более
137 строк, документация API — 161 строка; ответственности разделены,
добавления крупных компонентов нет.
Production/deployment не изменялись.
