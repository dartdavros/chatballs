---
id: T-009
title: Схема своих полей в конфигурации веб-подключения
milestone: M02
status: done
depends_on: []
order: 1
spec: "0019"
created: 2026-09-29
branch: skaro/T-009-shema-svoih-poley-v-konfigurat
archived: true
---

## Цель

Сервер принимает и валидирует config.fields WEB-подключения и отдаёт схему виджету без aiVisible (R-1, R-2, R-8).

## Критерии приёмки

- [x] PATCH подключения с fields валидирует ключ ^[a-z][a-z0-9_]{0,39}$, уникальность, неизменяемость ключа, label до 60 символов, тип из списка, options только у enum
- [x] Больше 30 полей и ключи name/email/phone отклоняются понятной ошибкой через t()
- [x] Публичная конфигурация /webchat/config отдаёт fields без aiVisible
- [x] Тесты на валидацию и публичную конфигурацию проходят (--reuse-db, только затронутые)

## Заметки

integrations: сериализатор config WEB (camelCase в API, snake_case в БД); webchat/widgets.py ensure_widget → presentation_config; webchat/services.py public_config.

## Итог

Схема своих полей хранится в config.fields WEB-подключения и проверяется при PATCH: формат и уникальность ключа, запрет смены ключа по служебному id, который выдаёт сервер (так решил владелец), название до 60 символов, тип из списка, значения только у списка, не больше 30 полей, ключи name/email/phone заняты. Все ошибки идут через t(), в ru и en. Настройки подключения отдают схему в camelCase, а /webchat/config — без aiVisible и id. Если форма присылает config без fields, схема не затирается.
