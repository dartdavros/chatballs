from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability
from hub_platform.identity.audit import record_audit_event
from hub_platform.integrations.models import Integration
from hub_platform.integrations.selectors import (
    integration_for_context,
    integrations_for_context,
)
from hub_platform.integrations.serializers import integration_payload
from hub_platform.integrations.services import (
    IntegrationInput,
    create_integration,
    delete_integration,
    test_integration,
    update_integration,
)


def _input(body: dict[str, object], *, current: Integration | None = None) -> IntegrationInput:
    config = body.get("config", current.config if current else {})
    raw_channel = body.get("channelId", current.channel_id if current else None)
    channel_id = int(raw_channel) if isinstance(raw_channel, int) or (isinstance(raw_channel, str) and raw_channel.isdigit()) else None
    return IntegrationInput(
        provider=str(body.get("provider", current.provider if current else "")),
        name=str(body.get("name", current.name if current else "")),
        secret=body.get("secret") if "secret" in body else None,
        config=config if isinstance(config, dict) else {},
        channel_id=channel_id,
        is_active=(
            body["isActive"]
            if isinstance(body.get("isActive"), bool)
            else (current.is_active if current else None)
        ),
    )


def _validation_error(error: Exception) -> Response:
    if isinstance(error, ValidationError):
        if hasattr(error, "message_dict"):
            detail = "; ".join(message for messages in error.message_dict.values() for message in messages)
        else:
            detail = "; ".join(error.messages)
    else:
        detail = "Интеграция с таким именем уже существует"
    return Response({"detail": detail}, status=400)


def _audit(request: Request, action: str, integration: Integration) -> None:
    record_audit_event(
        action=action,
        actor=request.user,
        organization=request.tenant_context.organization,
        object_type="Integration",
        object_id=str(integration.id),
        request=request,
    )


class IntegrationListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "integrations.view", "POST": "integrations.manage"}
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        items = integrations_for_context(request.tenant_context)
        return Response({"items": [integration_payload(item) for item in items]})

    def post(self, request: Request) -> Response:
        try:
            integration = create_integration(
                context=request.tenant_context, data=_input(request.data)
            )
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        _audit(request, "integrations.integration_created", integration)
        return Response({"integration": integration_payload(integration)}, status=201)


class IntegrationDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"
    require_organization_scope = True

    def _get(self, request: Request, integration_id: int) -> Integration:
        return integration_for_context(
            context=request.tenant_context, integration_id=integration_id
        )

    def patch(self, request: Request, integration_id: int) -> Response:
        try:
            integration = self._get(request, integration_id)
            integration = update_integration(
                context=request.tenant_context,
                integration=integration,
                data=_input(request.data, current=integration),
            )
        except Integration.DoesNotExist:
            return Response({"detail": "Интеграция не найдена"}, status=404)
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        _audit(request, "integrations.integration_updated", integration)
        return Response({"integration": integration_payload(integration)})

    def delete(self, request: Request, integration_id: int) -> Response:
        try:
            integration = self._get(request, integration_id)
        except Integration.DoesNotExist:
            return Response({"detail": "Интеграция не найдена"}, status=404)
        _audit(request, "integrations.integration_deleted", integration)
        delete_integration(context=request.tenant_context, integration=integration)
        return Response(status=204)


class IntegrationTestView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"
    require_organization_scope = True

    def post(self, request: Request, integration_id: int) -> Response:
        try:
            integration = integration_for_context(
                context=request.tenant_context, integration_id=integration_id
            )
        except Integration.DoesNotExist:
            return Response({"detail": "Интеграция не найдена"}, status=404)
        integration = test_integration(
            context=request.tenant_context, integration=integration
        )
        _audit(request, "integrations.integration_tested", integration)
        return Response({"integration": integration_payload(integration)})
