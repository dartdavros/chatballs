"""Audit selection and filters shared by HTTP and native actions."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone as django_timezone
from rest_framework.exceptions import PermissionDenied

from chatballs.i18n import t
from chatballs.identity.administration_payloads import audit_event_payload
from chatballs.identity.audit_catalog import (
    AUDIT_CATEGORY_ALIASES,
    AUDIT_RESULT_LABELS,
    audit_categories,
    audit_result_label,
)
from chatballs.identity.models import AuditEvent
from chatballs.identity.policy import has_capability_any_scope

AUDIT_PAGE_SIZE_DEFAULT = 25
AUDIT_PAGE_SIZE_MAX = 100
AUDIT_PERIODS = {"today": 0, "7d": 7, "30d": 30, "90d": 90}


def _audit_period_start(period: str, timezone_name: str):
    """Начало периода в часовом поясе организации, а не в UTC: «сегодня» должно
    означать сегодня у того, кто смотрит журнал."""
    if period not in AUDIT_PERIODS:
        return None
    now = django_timezone.localtime(timezone=ZoneInfo(timezone_name))
    start_day = (now - timedelta(days=AUDIT_PERIODS[period])).date()
    return django_timezone.make_aware(datetime.combine(start_day, time.min), now.tzinfo)


def _audit_actors(base) -> list[dict[str, object]]:
    """Кто вообще что-то делал в этой организации — для фильтра «Сотрудник».

    `order_by()` обязателен: у AuditEvent есть Meta.ordering, а поля сортировки
    Django подмешивает в SELECT перед DISTINCT. Без сброса уникальность считается
    по паре «сотрудник + время события», и сотрудник попадает в фильтр столько
    раз, сколько совершил действий.
    """
    rows = (
        base.filter(actor__isnull=False)
        .order_by()
        .values("actor_id", "actor__full_name", "actor__email")
        .distinct()
    )
    actors = [
        {"value": str(row["actor_id"]), "label": row["actor__full_name"] or row["actor__email"]}
        for row in rows
    ]
    actors.sort(key=lambda item: str(item["label"]).lower())
    if base.filter(actor__isnull=True).exists():
        actors.append({"value": "system", "label": t("admin.actor_system")})
    return actors


def list_audit(context, params):
    if not has_capability_any_scope(context.membership, "audit.view"):
        raise PermissionDenied()
    organization_id = context.organization_id
    base = AuditEvent.objects.filter(organization_id=organization_id)
    events = base.select_related("actor")
    period = str(params.get("period", "")).strip()
    since = _audit_period_start(period, context.organization.timezone)
    if since is not None:
        events = events.filter(created_at__gte=since)
    category = str(params.get("category", "")).strip()
    if category:
        prefixes = {category} | {
            alias for alias, target in AUDIT_CATEGORY_ALIASES.items() if target == category
        }
        condition = Q()
        for prefix in prefixes:
            condition |= Q(action__startswith=f"{prefix}.")
        events = events.filter(condition)
    result = str(params.get("result", "")).strip().upper()
    if result in AUDIT_RESULT_LABELS:
        events = events.filter(result=result)
    actor = str(params.get("actor", "")).strip()
    if actor == "system":
        events = events.filter(actor__isnull=True)
    elif actor.isdigit():
        events = events.filter(actor_id=int(actor))
    query = str(params.get("q", "")).strip()
    if query:
        events = events.filter(
            Q(action__icontains=query)
            | Q(object_type__icontains=query)
            | Q(object_id__icontains=query)
            | Q(actor__full_name__icontains=query)
            | Q(actor__email__icontains=query)
        )
    try:
        page_size = int(params.get("pageSize", AUDIT_PAGE_SIZE_DEFAULT))
    except (TypeError, ValueError):
        page_size = AUDIT_PAGE_SIZE_DEFAULT
    page_size = max(1, min(page_size, AUDIT_PAGE_SIZE_MAX))
    try:
        page = int(params.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)
    total = events.count()
    page_count = max(1, -(-total // page_size))
    page = min(page, page_count)
    start = (page - 1) * page_size
    rows = events.order_by("-created_at", "-id")[start : start + page_size]
    return {
        "items": [audit_event_payload(event) for event in rows],
        "page": page,
        "pageSize": page_size,
        "pageCount": page_count,
        "total": total,
        "filters": {
            "categories": audit_categories(),
            "results": [
                {"value": key, "label": audit_result_label(key)} for key in AUDIT_RESULT_LABELS
            ],
            "actors": _audit_actors(base),
        },
    }
