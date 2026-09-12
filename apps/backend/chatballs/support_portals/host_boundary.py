from __future__ import annotations

import sys

from django.conf import settings
from django.db import connections
from django.http import HttpRequest, HttpResponseBadRequest

from chatballs.support_portals.addressing import normalize_domain
from chatballs.tenancy.ingress import support_portal_route


class SupportPortalHostBoundaryMiddleware:
    """Accept app hosts and hosts present in the published portal directory.

    Пока установка не прошла мастер первого запуска, адрес себе она не знает:
    человек поднял докер на сервере и открывает её по IP или по своему домену.
    Отвечать на это «Invalid host» — значит не дать дойти до мастера, поэтому
    до создания первой организации принимается любой хост: данных, порталов и
    ссылок, которые можно было бы отравить чужим Host, ещё нет. После
    установки список хостов снова закрыт.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        raw_host = request.META.get("HTTP_HOST") or request.META.get("SERVER_NAME", "")
        host = normalize_domain(raw_host.partition(":")[0])
        if not self._allowed(host) and not _instance_is_unconfigured():
            return HttpResponseBadRequest("Invalid host")
        return self.get_response(request)

    @staticmethod
    def _allowed(host: str) -> bool:
        if host == "testserver" and (
            "pytest" in sys.modules
            or any("pytest" in argument for argument in sys.argv)
            or str(connections["default"].settings_dict["NAME"]).startswith("test_")
        ):
            return True
        # Адреса, которые человек задал сам: тот, на котором прошли мастер, и
        # предыдущий — чтобы смена адреса в «Настройках» не выбрасывала того,
        # кто её делает, до того как новый домен вообще заработал. Промах
        # перечитывает кэш: соседний процесс gunicorn мог ещё не увидеть адрес,
        # который мастер записал секунду назад.
        from chatballs.identity.instance_settings import host_is_accepted

        try:
            if host_is_accepted(host):
                return True
        except Exception:
            pass
        for allowed in settings.CHATBALLS_APP_PRIMARY_HOSTS:
            normalized = normalize_domain(allowed.lstrip("."))
            if host == normalized or (
                allowed.startswith(".") and host.endswith(f".{normalized}")
            ):
                return True
        try:
            return support_portal_route(host) is not None
        except Exception:
            return False


# Признак «мастер ещё не пройден» кэшируется: до установки его спрашивает
# каждый запрос, а после установки он больше не меняется.
_configured = False


def _instance_is_unconfigured() -> bool:
    global _configured
    if _configured:
        return False
    from chatballs.identity.setup import instance_needs_setup

    try:
        needs_setup = instance_needs_setup()
    except Exception:
        # База ещё не поднялась: на этом этапе хост тем более не проверить.
        return True
    if not needs_setup and not settings.TESTING:
        # Кэш живёт на весь процесс — в проде это ровно то, что нужно
        # (после установки признак больше не меняется). В тестах каждый тест
        # начинается с пустой базы, и первый же из них, создавший
        # организацию, закрывал бы мастер всем остальным в том же процессе.
        _configured = True
    return needs_setup
