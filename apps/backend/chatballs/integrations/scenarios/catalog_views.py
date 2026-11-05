from rest_framework.response import Response

from chatballs.integrations.scenarios.catalog_queries import catalog
from chatballs.integrations.scenarios.views import ScenarioAPIView


class ScenarioCatalogView(ScenarioAPIView):
    def get(self, request):
        return Response(catalog(request.tenant_context))
