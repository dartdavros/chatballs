"""Organization settings API; protocol callbacks are a separate boundary."""

from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai.external_agents import config, config_bindings, config_keys
from chatballs.ai.external_agents.config_policy import invalid
from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.integrations.adapters.transport import TransportError
from chatballs.tenancy.database import tenant_atomic


class SettingsView(APIView):
    permission_classes = [HasCapability]
    required_capability = "settings.manage"
    tenant_manages_own_transaction = True

    def check_permissions(self, request):
        with tenant_atomic(request.tenant_context):
            super().check_permissions(request)

    def handle_exception(self, error):
        if isinstance(error, TransportError):
            failure = {"capabilities_access_denied": "access", "incompatible_capabilities": "incompatible"}.get(error.code, "unavailable")
            return Response({"detail": t("external.incompatible"), "failure": failure}, status=400)
        if isinstance(error, ValidationError):
            return Response({"detail": t("external.invalid")}, status=400)
        return super().handle_exception(error)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class FeatureView(SettingsView):
    def get(self, request):
        return Response(config.settings(request.tenant_context))

    def patch(self, request):
        return Response(config.set_feature(request.tenant_context, request.data))


class ConnectionListView(SettingsView):
    def post(self, request):
        return Response(config.create_connection(request.tenant_context, request.data), status=201)


class ConnectionView(SettingsView):
    def patch(self, request, connection_id):
        return Response(config.update_connection(request.tenant_context, connection_id, request.data))


class CheckView(SettingsView):
    def post(self, request, connection_id):
        if request.data:
            invalid()
        return Response(config_keys.check_connection(request.tenant_context, connection_id))


class KeyView(SettingsView):
    def post(self, request, connection_id):
        if request.data:
            invalid()
        return Response(config_keys.change_key(request.tenant_context, connection_id))

    def delete(self, request, connection_id):
        config_keys.change_key(request.tenant_context, connection_id, revoke=True)
        return Response(status=204)


class BindingView(SettingsView):
    def put(self, request, connection_id, agent_id):
        return Response(config_bindings.save_binding(request.tenant_context, connection_id, agent_id, request.data))

    def delete(self, request, connection_id, agent_id):
        config_bindings.remove_binding(request.tenant_context, connection_id, agent_id)
        return Response(status=204)


class ConfigurationView(SettingsView):
    def put(self, request, connection_id):
        from chatballs.ai.external_agents.settings_commands import save_configuration

        return Response(save_configuration(request.tenant_context, connection_id, request.data))


class TemplatePreviewView(SettingsView):
    def get(self, request, template_id):
        from chatballs.ai.external_agents.settings_catalog import template_preview

        return Response(template_preview(request.tenant_context, template_id))
