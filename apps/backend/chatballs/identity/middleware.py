"""Отметка активности сессии.

Карточка «Активные сессии» в «Профиле» (дизайн-базлайн v2, кадр P1) показывает,
когда сессия была активна. Отдельной таблицы нет: отметка живёт в самой сессии
и обновляется не чаще раза в минуту, чтобы не переписывать её на каждый запрос.
"""

from __future__ import annotations

from chatballs.identity.sessions import touch_session


class SessionActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and hasattr(request, "session"):
            touch_session(request)
        return self.get_response(request)
