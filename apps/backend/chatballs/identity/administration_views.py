from __future__ import annotations

from django.core.exceptions import ValidationError
from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.identity.administration_payloads import (
    administration_timezones,
    audit_event_payload,
    organization_settings_payload,
)
from chatballs.identity.administration_services import (
    OrganizationSettingsInput,
    delete_organization_logo,
    replace_organization_logo,
    update_organization_settings,
)
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import AuditEvent


def _validation_response(error: ValidationError) -> Response:
    if hasattr(error, "message_dict"):
        payload = {
            key: messages[0] if isinstance(messages, list) else str(messages)
            for key, messages in error.message_dict.items()
        }
        detail = next(iter(payload.values()), "Проверьте заполненные поля")
        return Response({"detail": detail, "errors": payload}, status=400)
    return Response({"detail": "; ".join(error.messages)}, status=400)


class OrganizationSettingsView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "settings.view",
        "PATCH": "settings.manage",
    }
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        return Response(
            {
                "organization": organization_settings_payload(
                    request.tenant_context.organization
                ),
                "timezones": administration_timezones(),
            }
        )

    def patch(self, request: Request) -> Response:
        organization = request.tenant_context.organization
        body = request.data
        try:
            organization = update_organization_settings(
                context=request.tenant_context,
                data=OrganizationSettingsInput(
                    name=str(body.get("name", organization.name)),
                    timezone=str(body.get("timezone", organization.timezone)),
                    currency=str(body.get("currency", organization.currency)),
                ),
            )
        except ValidationError as error:
            return _validation_response(error)
        record_audit_event(
            action="administration.organization_updated",
            actor=request.user,
            organization=organization,
            object_type="Organization",
            object_id=str(organization.public_id),
            request=request,
        )
        return Response({"organization": organization_settings_payload(organization)})


class OrganizationLogoView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    required_capabilities = {
        "POST": "settings.manage",
        "DELETE": "settings.manage",
    }
    require_organization_scope = True

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [HasCapability()]

    def get(self, request: Request):
        organization = request.tenant_context.organization
        if not organization.logo:
            return Response({"detail": "Логотип не загружен"}, status=404)
        return FileResponse(
            organization.logo.open("rb"),
            content_type=organization.logo_content_type or "application/octet-stream",
            filename="organization-logo",
        )

    def post(self, request: Request) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Выберите файл логотипа"}, status=400)
        try:
            organization = replace_organization_logo(
                context=request.tenant_context,
                upload=upload,
            )
        except ValidationError as error:
            return _validation_response(error)
        record_audit_event(
            action="administration.logo_updated",
            actor=request.user,
            organization=organization,
            object_type="Organization",
            object_id=str(organization.public_id),
            request=request,
        )
        return Response({"organization": organization_settings_payload(organization)})

    def delete(self, request: Request) -> Response:
        organization = delete_organization_logo(context=request.tenant_context)
        record_audit_event(
            action="administration.logo_deleted",
            actor=request.user,
            organization=organization,
            object_type="Organization",
            object_id=str(organization.public_id),
            request=request,
        )
        return Response({"organization": organization_settings_payload(organization)})


class AuditListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "audit.view"
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        events = (
            AuditEvent.objects.filter(
                organization_id=request.tenant_context.organization_id,
            )
            .select_related("actor")
            .order_by("-created_at")[:50]
        )
        return Response({"items": [audit_event_payload(event) for event in events]})


class LaunchChecklistView(APIView):
    """Чек-лист «Запуск» (SPEC-HUB-0031 §5, дизайн-базлайн v2): три шага с
    автоотметкой по факту. Скрытие блока — предпочтение клиента (localStorage)."""

    permission_classes = [HasCapability]
    required_capability = "settings.view"

    def get(self, request: Request) -> Response:
        from chatballs.channels.models import Channel
        from chatballs.identity.models import OrganizationMembership
        from chatballs.integrations.models import Integration, IntegrationKind

        organization_id = request.tenant_context.organization_id
        agent_created = Channel.objects.filter(organization_id=organization_id).exists()
        connection_bound = Integration.objects.filter(
            organization_id=organization_id,
            kind=IntegrationKind.MESSENGER,
            channel__isnull=False,
        ).exists()
        employee_invited = (
            OrganizationMembership.objects.filter(
                organization_id=organization_id
            ).count()
            > 1
            or request.tenant_context.organization.invitations.exists()
        )
        return Response(
            {
                "agentCreated": agent_created,
                "connectionBound": connection_bound,
                "employeeInvited": employee_invited,
                "done": agent_created and connection_bound and employee_invited,
            }
        )
