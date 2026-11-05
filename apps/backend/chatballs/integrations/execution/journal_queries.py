"""Shared journal queries retain the product visibility and pagination rules."""

from django.db.models import Q

from chatballs.identity.models import EmployeeRole
from chatballs.integrations.execution.payloads import run_payload
from chatballs.integrations.execution.permissions import ExecutionDenied, current_actor, view_run
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


def require_manager(tenant):
    if current_actor(tenant).membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN}:
        raise ExecutionDenied("permission")


def journal_rows(tenant):
    current_actor(tenant)
    return ScenarioRun.objects.filter(organization_id=tenant.organization_id,
        journal_cleared_at__isnull=True).select_related("initiator__user").prefetch_related("steps")


def listing(tenant, data):
    with tenant_atomic(tenant):
        return _listing(tenant, data)


def _listing(tenant, data):
    rows = journal_rows(tenant)
    conversation = data.get("conversation", "")
    if conversation.isdecimal() and len(conversation) < 16:
        from chatballs.conversations.access import require_conversation_action
        from chatballs.conversations.models import Conversation
        context = Conversation.objects.get(pk=int(conversation), organization_id=tenant.organization_id)
        require_conversation_action(tenant, context, "conversations.view")
        rows = rows.filter(conversation=context)
    else:
        require_manager(tenant)
    filters = {"connections": list(Integration.objects.filter(organization_id=tenant.organization_id,
        scenariostep__run__in=rows).distinct().values("id", "name")),
        "initiators": list(rows.values("initiator_id", "initiator__user__full_name").distinct())}
    query = data.get("q", "").strip()[:200]
    if query:
        match = Q(structure__name__icontains=query) | Q(initiator__user__full_name__icontains=query) | Q(conversation__contact__name__icontains=query)
        if query.isdecimal():
            match |= Q(pk=int(query)) | Q(conversation_id=int(query))
        rows = rows.filter(match)
    state = data.get("state")
    if state in {"running", "approval", "completed", "failed", "unknown", "cancelled", "pending", "queued", "reconciling", "decision"}:
        rows = rows.filter(state=state)
    group = data.get("group")
    if group == "attention":
        rows = rows.filter(state__in=("failed", "unknown", "approval", "decision"))
    elif group == "active":
        rows = rows.filter(finished_at__isnull=True)
    elif group == "finished":
        rows = rows.filter(finished_at__isnull=False)
    initiator = data.get("initiator", "")
    if initiator.isdecimal() and len(initiator) < 16:
        rows = rows.filter(initiator_id=int(initiator))
    if data.get("period") == "30":
        from datetime import timedelta

        from django.utils import timezone
        rows = rows.filter(created_at__gte=timezone.now() - timedelta(days=30))
    connection_id = data.get("connection", "")
    if connection_id.isdecimal() and len(connection_id) < 16:
        rows = rows.filter(steps__integration_id=int(connection_id)).distinct()
    after = data.get("before")
    if after:
        from django.utils.dateparse import parse_datetime
        date = parse_datetime(after)
        if date:
            rows = rows.filter(created_at__lte=date)
    page = data.get("page", "1")
    page = max(1, min(int(page), 100000)) if page.isdecimal() and len(page) < 7 else 1
    count = rows.count()
    items = rows.order_by("-created_at", "-pk")[(page - 1) * 25:page * 25]
    return {"items": [run_payload(row) for row in items], "count": count, "page": page, "pageSize": 25, "filters": filters}


def detail(tenant, public_id):
    with tenant_atomic(tenant):
        run = journal_rows(tenant).get(public_id=public_id)
        view_run(tenant, run)
        return {"run": run_payload(run, detail=True, tenant=tenant)}
