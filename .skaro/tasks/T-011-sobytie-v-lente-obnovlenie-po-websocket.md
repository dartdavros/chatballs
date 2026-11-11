---
id: T-011
title: Событие в ленте, обновление по WebSocket и siteFields в API
milestone: M02
status: done
depends_on:
  - T-010
order: 3
spec: "0019"
created: 2026-09-29
branch: skaro/T-011-sobytie-v-lente-obnovlenie-po
archived: true
---

## Цель

Изменение значения видно оператору сразу: системное событие в ленте открытого диалога, событие по WebSocket и поле siteFields в API диалога и контакта (R-12, R-13, R-16).

## Критерии приёмки

- [x] Новый код SystemEvent для обновления данных сайта; параметры — подпись, старое и новое отображаемое значение; фразу собирает бэкенд через t() на языке читателя, ключи есть в ru и en
- [x] Событие пишется только для полей enum и boolean и только при фактическом изменении значения при открытом диалоге
- [x] Оператор получает событие по WebSocket, useConversationEvents обновляет карточку и ленту без перезагрузки
- [x] API диалога и контакта отдаёт siteFields [{key,label,type,value,display,color?,updatedAt}] в порядке схемы, без удалённых полей
- [x] Тесты событий, realtime и каталога i18n проходят (только затронутые)

## Заметки

conversations/models.py SystemEvent (+миграция choices), serializers.py _system_text, features/conversations/useConversationEvents.ts.

## Итог

Ветка T-011 перенесена через git rebase main на 416e37e4; конфликт webchat/services.py разрешён с сохранением sessions/configuration и preChatFields из main, а история сообщений подключена из message_history. Переписанные коммиты 3ba1b606 и d7ea4a97 сохранены, рабочее дерево чистое. Повторные адресные проверки после разрешения конфликта прошли.
