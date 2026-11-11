"""Organization journal and independently authorized per-conversation details."""

from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.conversations.models import Conversation
from chatballs.i18n import t
from chatballs.identity.models import EmployeeRole
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.errors import error_message
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.values import InvalidValues
from chatballs.integrations.service_connections.binding import ServiceUnavailable
from chatballs.integrations.service_connections.errors import ServiceCheckFailed


class RunAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        current_actor(request.tenant_context)

    def handle_exception(self, exc):
        if isinstance(exc, ServiceUnavailable) and exc.adapter:
            from chatballs.integrations.adapters.registry import default_registry
            from chatballs.integrations.service_connections.errors import error_payload
            error = error_payload(default_registry().adapter(exc.adapter), exc.code)
            return Response({"detail": f"{error.title} {error.text}".strip(), "error": error.as_dict()}, status=400)
        if isinstance(exc, InvalidValues):
            from chatballs.integrations.scenarios.payloads import issue_payload
            return Response({"detail": t("runs.error_arguments"), "issues": [issue_payload(issue) for issue in exc.issues]}, status=400)
        if isinstance(exc, Conversation.DoesNotExist | ScenarioRun.DoesNotExist | ScenarioDefinition.DoesNotExist | Integration.DoesNotExist | ExecutionDenied | ServiceUnavailable | ServiceCheckFailed | InvalidValues | ValidationError | ValueError | TypeError | KeyError):
            code = str(exc) if isinstance(exc, ExecutionDenied) else "unavailable"
            return Response({"detail": error_message(code)}, status=409 if isinstance(exc, ExecutionDenied) else 404)
        return super().handle_exception(exc)

    def rows(self, request):
        return ScenarioRun.objects.filter(organization_id=request.tenant_context.organization_id,
            journal_cleared_at__isnull=True).select_related("initiator__user").prefetch_related("steps")

    def manager(self, request):
        if current_actor(request.tenant_context).membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
            raise ExecutionDenied("permission")


class RunListView(RunAPIView):
    def get(self, request):
        from chatballs.integrations.execution.journal_queries import listing
        return Response(listing(request.tenant_context, request.query_params))


class RunDetailView(RunAPIView):
    def get(self, request, public_id):
        from chatballs.integrations.execution.journal_queries import detail
        return Response(detail(request.tenant_context, public_id))


class RunControlView(RunAPIView):
    def post(self, request, public_id, action):
        data = request.data if isinstance(request.data, dict) else {}
        if action == "repeat":
            from chatballs.integrations.execution.repeat import intentional_repeat
            run = intentional_repeat(request.tenant_context, public_id,
                trigger_key=data.get("triggerKey"), acknowledged=data.get("acknowledged"), manual_validation=True)
        else:
            if action == "resolve":
                from chatballs.integrations.scenarios.conflicts import resolve
                run = resolve(request.tenant_context, public_id, expected_digest=data.get("digest"), choices=data.get("choices"))
            elif action == "decide":
                from chatballs.integrations.execution.wait_controls import decide
                run = decide(request.tenant_context, public_id, path=data.get("path"), generation=data.get("generation"),
                    digest=data.get("digest"), accepted=data.get("accepted"))
            else:
                run = control(tenant=request.tenant_context, public_id=public_id, action=action,
                              digest=data.get("digest"), path=data.get("path"), arguments=data.get("arguments"), edit_token=data.get("editToken"))
        return Response({"run": run_payload(run, detail=True, tenant=request.tenant_context)})
