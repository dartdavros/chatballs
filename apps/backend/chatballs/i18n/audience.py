"""Язык текста, который уходит наружу — клиенту, а не сотруднику.

Язык запроса здесь не годится. Приглашение на звонок, просьба поделиться
контактом, тема исходящего письма — это речь организации, обращённая к её
клиенту, и она не должна менять язык от того, кто из операторов нажал кнопку.
Часть такого текста вообще рождается в воркере, где запроса нет.

Поэтому берём язык организации, а если она его не задавала — язык установки.
Язык самого клиента нам неизвестен: в Telegram, MAX и почте его сообщить
нечему, а в веб-виджете он выбирается на стороне страницы.
"""

from __future__ import annotations

from chatballs.i18n.languages import INHERIT, first_chosen, normalize_language


def customer_language(organization: object) -> str:
    """Язык обращения организации к клиенту. Пусто — язык по умолчанию."""

    from chatballs.identity.instance_settings import default_language

    organization_language = normalize_language(getattr(organization, "language", INHERIT))
    return first_chosen(organization_language, default_language())
