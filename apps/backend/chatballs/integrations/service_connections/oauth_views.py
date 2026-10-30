"""Вход через сервис: начало, состояние и возврат (SPEC-0037 R-7).

Начать вход и узнать его состояние может только сотрудник с правом
управлять интеграциями, и только свой. Возврат приходит без организации в
адресе: её выводит сервер из одноразового state.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.integrations.models import ServiceOAuthState
from chatballs.integrations.service_connections import oauth
from chatballs.integrations.service_connections.payloads import oauth_state_payload
from chatballs.integrations.service_connections.views import (
    ServiceAPIView,
    access_input,
    connection_for,
    invalid,
    not_found,
)
from chatballs.tenancy.database import tenant_atomic

SERVICES_ROUTE = "/settings/integrations/services"


class ServiceOAuthStartView(ServiceAPIView):
    required_capability = "integrations.manage"

    def post(self, request: Request) -> Response:
        data = access_input(request)
        connection_id = request.data.get("connectionId") if isinstance(request.data, dict) else None
        integration = connection_for(request, int(connection_id)) if str(connection_id or "").isdigit() else None
        if connection_id and integration is None:
            return not_found()
        try:
            state, url = oauth.start_oauth(context=request.tenant_context, data=data, integration=integration)
        except ValidationError as error:
            return invalid(error)
        return Response({"state": oauth_state_payload(state), "authorizeUrl": url}, status=201)


class ServiceOAuthStateView(ServiceAPIView):
    required_capability = "integrations.manage"

    def get(self, request: Request, state_id: str) -> Response:
        with tenant_atomic(request.tenant_context):
            state = ServiceOAuthState.objects.filter(
                public_id=state_id, organization_id=request.tenant_context.organization_id, user=request.user
            ).first()
            if state is None:
                return not_found()
            return Response({"state": oauth_state_payload(state)})


class ServiceOAuthCallbackView(APIView):
    """Возврат из сервиса. Организация выводится из state на сервере."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> HttpResponseRedirect:
        try:
            oauth.complete_oauth(
                user=request.user,
                token=str(request.query_params.get("state", "")),
                code=str(request.query_params.get("code", "")),
                error=str(request.query_params.get("error", "")),
            )
        except oauth.OAuthFailed:
            pass
        # Окно входа закрывается само; результат форма читает по своему state.
        return HttpResponseRedirect(f"{SERVICES_ROUTE}?serviceOauth=done")
