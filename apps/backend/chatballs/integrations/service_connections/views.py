"""HTTP adapters for service management and its original OAuth protocol."""

from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.deletion import IntegrationInUse
from chatballs.integrations.models import Integration
from chatballs.integrations.service_connections import management as commands
from chatballs.integrations.service_connections import management_reads as reads
from chatballs.integrations.service_connections.errors import error_payload
from chatballs.tenancy.database import tenant_atomic


def invalid(error):
    errors = error.message_dict if hasattr(error, "message_dict") else {"detail": error.messages}
    detail = "; ".join(message for messages in errors.values() for message in messages)
    return Response({"detail": detail, "errors": errors}, status=400)


def not_found():
    return Response({"detail": t("services.not_found")}, status=404)


def connection_for(request, connection_id):
    try:
        return reads.load(request.tenant_context, connection_id, "integrations.manage")
    except Integration.DoesNotExist:
        return None


def access_input(request):
    return commands.access_data(request.data)


class ServiceAPIView(APIView):
    permission_classes = [HasCapability]
    tenant_manages_own_transaction = True

    def check_permissions(self, request):
        with tenant_atomic(request.tenant_context):
            super().check_permissions(request)

    def result(self, request, operation, *args, response_status=200, audited=False):
        try:
            kwargs = {"request": request} if audited else {}
            payload = operation(request.tenant_context, *args, **kwargs)
        except Integration.DoesNotExist:
            return not_found()
        except ValidationError as error:
            return invalid(error)
        except IntegrationInUse as error:
            return Response({"detail": str(error)}, status=409)
        except commands.ManagementCheckFailed as error:
            adapter = default_registry().adapter(error.adapter)
            return Response({**error.payload, "error": error_payload(adapter, error.code).as_dict()}, status=400)
        return Response(payload if response_status != 204 else None, status=response_status)


class ServiceAdapterListView(ServiceAPIView):
    required_capability = "integrations.view"

    def get(self, request):
        return self.result(request, reads.adapters)


class ServiceConnectionListView(ServiceAPIView):
    required_capabilities = {"GET": "integrations.view", "POST": "integrations.manage"}

    def get(self, request):
        return self.result(request, reads.listing)

    def post(self, request):
        return self.result(request, commands.create, request.data, response_status=201, audited=True)


class ServiceConnectionDetailView(ServiceAPIView):
    required_capabilities = {"GET": "integrations.view", "PATCH": "integrations.manage", "DELETE": "integrations.manage"}

    def get(self, request, connection_id):
        return self.result(request, reads.detail, connection_id)

    def patch(self, request, connection_id):
        return self.result(request, commands.update, connection_id, request.data, audited=True)

    def delete(self, request, connection_id):
        return self.result(request, commands.delete, connection_id, response_status=204, audited=True)


class ServiceConnectionCheckView(ServiceAPIView):
    required_capability = "integrations.manage"

    def post(self, request, connection_id):
        return self.result(request, commands.check, connection_id, request.data, audited=True)


class ServiceConnectionAccessView(ServiceAPIView):
    required_capability = "integrations.manage"

    def post(self, request, connection_id):
        return self.result(request, commands.replace_access, connection_id, request.data, audited=True)


class ServiceLookupView(ServiceAPIView):
    required_capability = "integrations.manage"

    def get(self, request, connection_id, key):
        return self.result(request, commands.lookup, connection_id, key)
