"""Public signed ingress: organization comes from the stored connection."""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from chatballs.integrations.automation_events.ingress import receive
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.ingress import _unique_route
from chatballs.tenancy.lookup import load_organization


@method_decorator(csrf_exempt, name="dispatch")
class ServiceEventView(View):
    def post(self, request, connection_id, event_key):
        # Integration is an existing globally routed resource like messenger ingress.
        route = _unique_route("service_event_directory", str(connection_id))
        if route is None:
            return JsonResponse({"code": "not_found"}, status=404)
        if int(request.META.get("CONTENT_LENGTH") or 0) > 256 * 1024:
            return JsonResponse({"code": "too_large"}, status=413)
        tenant = TenantContext.for_resource(load_organization(route.organization_id))
        try:
            _, created = receive(tenant, int(route.resource_id), event_key, request.body, dict(request.headers))
        except (ExecutionDenied, ValueError):
            return JsonResponse({"code": "invalid_event"}, status=400)
        return JsonResponse({"accepted": True, "duplicate": not created})
