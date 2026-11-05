from rest_framework.response import Response

from chatballs.integrations.scenarios import synchronization_management as management
from chatballs.integrations.scenarios.views import ScenarioAPIView


class ServiceSynchronizationView(ScenarioAPIView):
    def get(self, request, connection_id):
        return Response(management.detail(request.tenant_context, connection_id))

    def put(self, request, connection_id):
        return Response(management.save(request.tenant_context, connection_id, request.data, request=request))
