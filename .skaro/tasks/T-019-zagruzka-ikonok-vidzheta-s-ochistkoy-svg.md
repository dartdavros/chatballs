---
id: T-019
title: Загрузка иконок виджета с очисткой SVG
milestone: M04
status: done
depends_on: []
order: 1
spec: "0021"
created: 2026-09-29
branch: skaro/T-019-zagruzka-ikonok-vidzheta-s-och
archived: true
---

## Цель

Администратор загружает SVG или PNG для кнопки и шапки; файл безопасен и отдаётся публично (R-3, R-4).

## Критерии приёмки

- [x] POST /api/v1/integrations/{id}/assets/ принимает SVG/PNG до 256 КБ, PNG от 96×96, возвращает {url}; остальное отклоняется понятной ошибкой
- [x] SVG очищается на сервере: script, on*, foreignObject, внешние href/xlink:href, javascript: удалены (тест с вредным SVG)
- [x] Файл лежит в хранилище организации organizations/{public_id}/…, работает и на диске, и на S3
- [x] Файл отдаётся виджету на чужом сайте без авторизации, чужая организация не может перезаписать

## Итог

Добавлен POST /api/v1/organizations/{org}/integrations/{id}/assets/: он принимает SVG или PNG до 256 КБ (PNG от 96×96) и возвращает { url }. SVG очищается на сервере до сохранения. Файл хранится в папке организации на диске или в S3 и отдаётся без авторизации по непредсказуемому UUID (GET /api/v1/webchat/assets/<uuid>/). Модель WidgetAsset защищена RLS, триггерами связей и каталогом входа. При удалении интеграции её иконки стираются.
