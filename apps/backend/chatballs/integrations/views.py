"""Thin HTTP adapters for the shared integration management commands."""

from functools import partial

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.integrations import management
from chatballs.integrations.deletion import IntegrationInUse
from chatballs.integrations.models import Integration
from chatballs.integrations.service_connections.views import invalid


class IntegrationAPIView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"

    def result(self, request, operation, *args, status=200, audited=True):
        try:
            result = operation(request.tenant_context, *args, **({"request": request} if audited else {}))
        except Integration.DoesNotExist:
            return Response({"detail": t("settings.integration_not_found")}, status=404)
        except ValidationError as error:
            return invalid(error)
        except IntegrityError:
            return Response({"detail": t("native.connections.name_taken")}, status=400)
        except IntegrationInUse as error:
            return Response({"detail": str(error)}, status=409)
        return Response(result if status != 204 else None, status=status)


class IntegrationListView(IntegrationAPIView):
    required_capabilities = {"GET": "integrations.view", "POST": "integrations.manage"}

    def get(self, request):
        return self.result(request, management.listing, audited=False)

    def post(self, request):
        return self.result(request, management.create, request.data, status=201)


class IntegrationDetailView(IntegrationAPIView):
    def patch(self, request, integration_id):
        return self.result(request, management.update, integration_id, request.data)

    def delete(self, request, integration_id):
        return self.result(request, management.delete, integration_id, status=204)


class IntegrationTestView(IntegrationAPIView):
    tenant_manages_own_transaction = True

    def check_permissions(self, request):
        from chatballs.tenancy.database import tenant_atomic

        with tenant_atomic(request.tenant_context):
            super().check_permissions(request)

    def post(self, request, integration_id):
        return self.result(request, management.checked, integration_id, request.data)


class IntegrationToolsRefreshView(IntegrationAPIView):
    def post(self, request, integration_id):
        return self.result(request, partial(management.checked, refresh=True), integration_id)


class IntegrationToolConfirmView(IntegrationAPIView):
    def post(self, request, integration_id):
        return self.result(request, management.read_only, integration_id, request.data)


class IntegrationToolRevokeView(IntegrationAPIView):
    def post(self, request, integration_id):
        return self.result(request, partial(management.read_only, revoke=True), integration_id, request.data)
