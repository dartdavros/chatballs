"""Scoped Bearer ingress: identity is resolved from a narrow routing directory."""

import hmac
import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from chatballs.integrations.execution.automation import launch_automatic
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.subscriptions import ScenarioExternalKey
from chatballs.integrations.scenarios.external_keys import token_hash
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import _unique_route
from chatballs.tenancy.lookup import load_organization


@method_decorator(csrf_exempt, name="dispatch")
class ScenarioTriggerView(View):
    def post(self, request, public_id):
        route = _unique_route("scenario_trigger_directory", str(public_id))
        token = request.headers.get("Authorization", "")
        if route is None or not token.startswith("Bearer ") or len(token) > 512:
            return JsonResponse({"code": "unauthorized"}, status=401)
        tenant = TenantContext.for_resource(load_organization(route.organization_id))
        if len(request.body) > 256 * 1024:
            return JsonResponse({"code": "too_large"}, status=413)
        try:
            data = json.loads(request.body)
            if not isinstance(data, dict) or set(data) - {"parameters", "conversationId"}:
                raise ValueError()
            key = request.headers.get("Idempotency-Key", "")
            if not 1 <= len(key) <= 100 or not isinstance(data.get("parameters", {}), dict):
                raise ValueError()
            conversation_id = data.get("conversationId")
            if conversation_id is not None and type(conversation_id) is not int:
                raise ValueError()
            with tenant_atomic(tenant):
                credential = ScenarioExternalKey.objects.get(pk=route.resource_id)
                if not hmac.compare_digest(credential.token_hash, token_hash(token[7:])):
                    return JsonResponse({"code": "unauthorized"}, status=401)
                scenario = ScenarioDefinition.objects.select_for_update().get(pk=credential.scenario_id)
                credential = ScenarioExternalKey.objects.select_for_update().get(pk=route.resource_id)
                if not hmac.compare_digest(credential.token_hash, token_hash(token[7:])):
                    return JsonResponse({"code": "unauthorized"}, status=401)
                credential.scenario = scenario
                trigger = next((t for t in credential.scenario.definition["triggers"]
                    if t["kind"] == "api" and t["id"] == credential.trigger_id), None)
                if trigger is None:
                    raise ExecutionDenied("permission")
                run, created = launch_automatic(tenant, credential.scenario, trigger,
                    key=f"api:{credential.trigger_id}:{key}", parameters=data.get("parameters", {}), conversation_id=conversation_id)
                return JsonResponse({"id": str(run.public_id), "state": run.state, "duplicate": not created}, status=202)
        except ExecutionDenied as error:
            return JsonResponse({"code": str(error)}, status=403)
        except (ValueError, TypeError, ScenarioExternalKey.DoesNotExist):
            return JsonResponse({"code": "invalid_request"}, status=400)
