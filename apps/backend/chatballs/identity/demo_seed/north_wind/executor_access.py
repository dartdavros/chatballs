"""The isolated executor can obtain only its own demo callback and shop keys."""

from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai.external_agents.auth import key_hash
from chatballs.ai.external_agents.config_models import ExternalAgentConnection
from chatballs.identity.demo_models import DemoDataset
from chatballs.identity.demo_seed.north_wind.executor_scope import (
    active_executor,
    inbound_key,
    read_executor_key,
)
from chatballs.identity.demo_seed.north_wind.local_access import issue_local_read_token
from chatballs.tenancy.database import tenant_atomic


class DemoExecutorAccessView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, stage):
        if stage not in {"probe", "runtime", "retired"}:
            raise NotFound()
        binding = read_executor_key(request.headers.get("Authorization"))
        if binding is None:
            raise PermissionDenied()
        if stage == "probe":
            return Response(status=204)
        organization_id, generation, connection_id = binding
        with tenant_atomic(organization_id):
            if stage == "retired":
                if DemoDataset.objects.filter(organization_id=organization_id, generation=generation).exists():
                    raise PermissionDenied()
                return Response({"connectionId": str(connection_id), "generation": generation},
                                headers={"Cache-Control": "no-store"})
            connection = ExternalAgentConnection.objects.filter(
                organization_id=organization_id, pk=connection_id,
            ).select_related("integration__service_settings").first()
            dataset = active_executor(organization_id, connection) if connection else None
            if dataset is None or str(dataset.generation) != generation:
                raise PermissionDenied()
            callback = inbound_key(dataset, connection_id)
            if connection.inbound_key_hash != key_hash(callback):
                raise PermissionDenied()
            payload = {
                "connectionId": str(connection_id), "generation": generation, "callbackKey": callback,
                "shopKey": issue_local_read_token(dataset, customer="andrey-after-purchase"),
            }
        return Response(payload, headers={"Cache-Control": "no-store"})
