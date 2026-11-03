"""Organization journal and independently authorized per-conversation details."""

from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from chatballs.i18n import t
from chatballs.identity.models import EmployeeRole
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.errors import error_message
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor, view_run
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.models import Integration
from django.core.exceptions import ValidationError
from chatballs.conversations.models import Conversation
from chatballs.integrations.service_connections.binding import ServiceUnavailable
from chatballs.integrations.service_connections.errors import ServiceCheckFailed
from chatballs.integrations.scenarios.values import InvalidValues


class RunAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        current_actor(request.tenant_context)

    def handle_exception(self, exc):
        if isinstance(exc, InvalidValues):
            from chatballs.integrations.scenarios.payloads import issue_payload
            return Response({"detail": t("runs.error_arguments"), "issues": [issue_payload(issue) for issue in exc.issues]}, status=400)
        if isinstance(exc, (Conversation.DoesNotExist, ScenarioRun.DoesNotExist, ScenarioDefinition.DoesNotExist, Integration.DoesNotExist,
                            ExecutionDenied, ServiceUnavailable, ServiceCheckFailed, InvalidValues, ValidationError, ValueError, TypeError, KeyError)):
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
        rows = self.rows(request)
        conversation = request.query_params.get("conversation", "")
        if conversation.isdecimal() and len(conversation) < 16:
            from chatballs.conversations.models import Conversation
            from chatballs.conversations.access import require_conversation_action
            context = Conversation.objects.get(pk=int(conversation), organization_id=request.tenant_context.organization_id)
            require_conversation_action(request.tenant_context, context, "conversations.view")
            rows = rows.filter(conversation=context)
        else:
            self.manager(request)
        filters = {"connections": list(Integration.objects.filter(organization_id=request.tenant_context.organization_id,
            scenariostep__run__in=rows).distinct().values("id", "name")),
            "initiators": list(rows.values("initiator_id", "initiator__user__full_name").distinct())}
        query = request.query_params.get("q", "").strip()[:200]
        if query:
            match = Q(structure__name__icontains=query) | Q(initiator__user__full_name__icontains=query) | Q(conversation__contact__name__icontains=query)
            if query.isdecimal():
                match |= Q(pk=int(query)) | Q(conversation_id=int(query))
            rows = rows.filter(match)
        state = request.query_params.get("state")
        if state in {"running", "approval", "completed", "failed", "unknown", "cancelled", "pending", "queued", "reconciling"}:
            rows = rows.filter(state=state)
        group = request.query_params.get("group")
        if group == "attention":
            rows = rows.filter(state__in=("failed", "unknown", "approval"))
        elif group == "active":
            rows = rows.filter(finished_at__isnull=True)
        elif group == "finished":
            rows = rows.filter(finished_at__isnull=False)
        initiator = request.query_params.get("initiator", "")
        if initiator.isdecimal() and len(initiator) < 16:
            rows = rows.filter(initiator_id=int(initiator))
        if request.query_params.get("period") == "30":
            from datetime import timedelta
            from django.utils import timezone
            rows = rows.filter(created_at__gte=timezone.now() - timedelta(days=30))
        connection_id = request.query_params.get("connection", "")
        if connection_id.isdecimal() and len(connection_id) < 16:
            rows = rows.filter(steps__integration_id=int(connection_id)).distinct()
        after = request.query_params.get("before")
        if after:
            from django.utils.dateparse import parse_datetime
            date = parse_datetime(after)
            if date:
                rows = rows.filter(created_at__lte=date)
        page = request.query_params.get("page", "1")
        page = max(1, min(int(page), 100000)) if page.isdecimal() and len(page) < 7 else 1
        count = rows.count()
        items = rows.order_by("-created_at", "-pk")[(page - 1) * 25:page * 25]
        return Response({"items": [run_payload(row) for row in items], "count": count, "page": page, "pageSize": 25, "filters": filters})


class RunDetailView(RunAPIView):
    def get(self, request, public_id):
        run = self.rows(request).get(public_id=public_id)
        view_run(request.tenant_context, run)
        return Response({"run": run_payload(run, detail=True, tenant=request.tenant_context)})


class RunControlView(RunAPIView):
    def post(self, request, public_id, action):
        data = request.data if isinstance(request.data, dict) else {}
        if action == "repeat":
            from chatballs.integrations.execution.repeat import intentional_repeat
            run = intentional_repeat(request.tenant_context, public_id,
                trigger_key=data.get("triggerKey"), acknowledged=data.get("acknowledged"))
        else:
            if action == "decide":
                from chatballs.integrations.execution.wait_controls import decide
                run = decide(request.tenant_context, public_id, path=data.get("path"), generation=data.get("generation"),
                    digest=data.get("digest"), accepted=data.get("accepted"))
            else:
                run = control(tenant=request.tenant_context, public_id=public_id, action=action,
                              digest=data.get("digest"), path=data.get("path"))
        return Response({"run": run_payload(run, detail=True, tenant=request.tenant_context)})
