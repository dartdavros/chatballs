from __future__ import annotations

from django.core.exceptions import ValidationError
from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import CloudDeliveryOnly, HasCapability
from hub_platform.identity.administration_payloads import (
    administration_timezones,
    audit_event_payload,
    organization_settings_payload,
    subscription_payload,
)
from hub_platform.identity.administration_services import (
    OrganizationSettingsInput,
    delete_organization_logo,
    replace_organization_logo,
    update_organization_settings,
)
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import AuditEvent
from hub_platform.subscriptions.models import Subscription


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


class SubscriptionSummaryView(APIView):
    permission_classes = [CloudDeliveryOnly, HasCapability]
    required_capability = "settings.view"
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        try:
            payload = subscription_payload(request.tenant_context)
        except Subscription.DoesNotExist:
            return Response({"detail": "Тариф организации не найден"}, status=404)
        return Response({"subscription": payload})


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
