"""HTTP administration entry points backed by the shared application services."""

from django.core.exceptions import ValidationError
from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.identity import organization_settings_commands as commands
from chatballs.identity.audit_queries import list_audit
from chatballs.identity.onboarding_views import OnboardingView as OnboardingView


def _validation_response(error):
    if hasattr(error, "message_dict"):
        payload = {key: messages[0] if isinstance(messages, list) else str(messages)
            for key, messages in error.message_dict.items()}
        return Response({"detail": next(iter(payload.values()), t("setup.check_fields")), "errors": payload}, status=400)
    return Response({"detail": "; ".join(error.messages)}, status=400)


class OrganizationSettingsView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "settings.view", "PATCH": "settings.manage"}

    def get(self, request):
        return Response(commands.read_settings(request.tenant_context))

    def patch(self, request):
        try:
            return Response(commands.update_settings(request.tenant_context, request.data, request=request))
        except ValidationError as error:
            return _validation_response(error)


class OrganizationLogoView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    required_capabilities = {"POST": "settings.manage", "DELETE": "settings.manage"}

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "GET" else [HasCapability()]

    def get(self, request):
        file, content_type = commands.read_logo(request.tenant_context)
        response = FileResponse(file.open("rb"), content_type=content_type, filename="organization-logo")
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def post(self, request):
        try:
            return Response(commands.upload_logo(request.tenant_context, request.FILES.get("file"), request=request))
        except ValidationError as error:
            return _validation_response(error)

    def delete(self, request):
        return Response(commands.remove_logo(request.tenant_context, request=request))


class AuditListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "audit.view"

    def get(self, request):
        return Response(list_audit(request.tenant_context, request.query_params))
