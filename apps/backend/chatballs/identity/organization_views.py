"""Создание организации из интерфейса: /api/v1/organizations/ без uuid в адресе.

Организации ещё нет, поэтому tenant middleware этот путь не трогает: контекст
открывает сам сервис вокруг вставки. Ответ повторяет форму ответа приглашения
(auth.invitations): обновлённая учётная запись со списком членств и публичный
id организации, в которую интерфейсу переключиться.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.identity.administration_payloads import (
    administration_languages,
    administration_timezones,
)
from chatballs.identity.administration_services import OrganizationSettingsInput
from chatballs.identity.auth.common import _user_payload, validation_response
from chatballs.identity.organization_creation import (
    can_create_organization,
    create_organization,
)


def _forbidden() -> Response:
    return Response({"detail": t("identity.organization_create_forbidden")}, status=403)


class OrganizationCreateOptionsView(APIView):
    """Справочники для формы: часовые пояса и языки, как в «Настройках»."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        if not can_create_organization(request.user):
            return _forbidden()
        return Response(
            {
                "timezones": administration_timezones(),
                "languages": administration_languages(),
                "currencies": ["RUB"],
            }
        )


class OrganizationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not can_create_organization(request.user):
            return _forbidden()
        body = request.data if isinstance(request.data, dict) else {}
        try:
            created = create_organization(
                data=OrganizationSettingsInput(
                    name=str(body.get("name", "")),
                    timezone=str(body.get("timezone", "") or "Europe/Moscow"),
                    currency=str(body.get("currency", "") or "RUB"),
                    language=str(body.get("language", "")),
                ),
                owner=request.user,
            )
        except ValidationError as error:
            return validation_response(error)
        return Response(
            {
                "user": _user_payload(request.user),
                "organizationPublicId": str(created.organization.public_id),
            },
            status=201,
        )
