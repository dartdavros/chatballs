---
id: T-013
title: Chatballs.setFields в лоадере и передача полей из виджета
milestone: M02
status: done
depends_on:
  - T-010
order: 5
spec: "0019"
created: 2026-09-29
branch: skaro/T-013-chatballs-setfields-v-loadere
archived: true
---

## Цель

Сайт может вызывать Chatballs.setFields() в любой момент, даже до загрузки скрипта, и значения доходят до сервера (R-5, R-6, R-7).

## Критерии приёмки

- [x] window.Chatballs с очередью q и методом setFields; вызовы до загрузки лоадера обрабатываются; window.ChatballsChat продолжает работать
- [x] Лоадер передаёт поля в свой iframe через postMessage({type:"chatballs-set-fields", fields}) с проверкой origin
- [x] Виджет сливает вызовы по ключам, null очищает; отправка не чаще раза в 500 мс
- [x] До старта сессии поля держатся в памяти и уходят вместе с startSession, после — POST /webchat/fields/
- [x] Сбой отправки не ломает виджет и страницу сайта

## Заметки

webchat/loader.py (LOADER_JS), web-chat/src/api.ts, App.tsx. Не раздувать App.tsx — вынести в отдельный модуль/хук.

## Итог

Ветка перенесена через git rebase main на b160335b; конфликт loader.py разрешён с сохранением оформления кнопки и модульной структуры из main. Передача полей встроена в loader_assets, дублирующие loader_scripts удалены; итоговый коммит e4f25642, рабочее дерево чистое. После разрешения конфликта прошли сборка, 6 Vitest-тестов передачи полей, 5 Node-тестов лоадера, Ruff, Django check и браузерная проверка реального dev-контура задачи.
