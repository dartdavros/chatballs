"""Активация языка на время одного запроса.

Стоит последней в цепочке — ближе всех к вьюхе, — потому что организацию
запроса определяет ``TenantContextMiddleware``, и до неё язык организации ещё
неизвестен. Активируется штатный механизм Django: от него зависят и наш
каталог, и сообщения DRF о невалидных полях.
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import translation

from chatballs.i18n.languages import INHERIT, first_chosen, resolve_language


class LanguageMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Язык установки спрашивается последним и только если до него дошло:
        # это чтение из базы, и запросу сотрудника со своим языком (или из
        # организации со своим) оно не нужно вовсе.
        language = first_chosen(
            self._user_language(request), self._organization_language(request)
        ) or resolve_language(
            instance_language=self._instance_language(),
            accept_language=request.headers.get("Accept-Language"),
        )
        with translation.override(language):
            request.LANGUAGE_CODE = language
            response = self.get_response(request)
        # Заголовок нужен кэшам и прокси: один и тот же URL отдаёт разный текст
        # для разных людей, и без Vary ответ одного уедет другому.
        response.setdefault("Content-Language", language)
        existing = response.get("Vary", "")
        if "accept-language" not in existing.lower():
            response["Vary"] = f"{existing}, Accept-Language".lstrip(", ")
        return response

    @staticmethod
    def _user_language(request: HttpRequest) -> str:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return INHERIT
        return getattr(user, "ui_language", INHERIT) or INHERIT

    @staticmethod
    def _organization_language(request: HttpRequest) -> str:
        context = getattr(request, "tenant_context", None)
        if context is None:
            return INHERIT
        return getattr(context.organization, "language", INHERIT) or INHERIT

    @staticmethod
    def _instance_language() -> str:
        from chatballs.identity.instance_settings import default_language

        return default_language()
