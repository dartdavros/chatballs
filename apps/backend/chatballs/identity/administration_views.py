from __future__ import annotations

from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone as django_timezone
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.identity.administration_payloads import (
    administration_languages,
    administration_timezones,
    audit_event_payload,
    organization_settings_payload,
)
from chatballs.identity.administration_services import (
    OrganizationSettingsInput,
    delete_organization_logo,
    replace_organization_logo,
    update_organization_settings,
)
from chatballs.identity.audit import record_audit_event
from chatballs.identity.audit_catalog import (
    AUDIT_CATEGORY_ALIASES,
    AUDIT_RESULT_LABELS,
    audit_categories,
    audit_result_label,
)
from chatballs.identity.models import AuditEvent


def _validation_response(error: ValidationError) -> Response:
    if hasattr(error, "message_dict"):
        payload = {
            key: messages[0] if isinstance(messages, list) else str(messages)
            for key, messages in error.message_dict.items()
        }
        detail = next(iter(payload.values()), "Проверьте заполненные поля")
        return Response({"detail": detail, "errors": payload}, status=400)
    return Response({"detail": "; ".join(error.messages)}, status=400)


class OrganizationSettingsView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "settings.view",
        "PATCH": "settings.manage",
    }

    def get(self, request: Request) -> Response:
        return Response(
            {
                "organization": organization_settings_payload(
                    request.tenant_context.organization
                ),
                "timezones": administration_timezones(),
                "languages": administration_languages(),
            }
        )

    def patch(self, request: Request) -> Response:
        organization = request.tenant_context.organization
        body = request.data
        try:
            organization = update_organization_settings(
                context=request.tenant_context,
                data=OrganizationSettingsInput(
                    name=str(body.get("name", organization.name)),
                    timezone=str(body.get("timezone", organization.timezone)),
                    currency=str(body.get("currency", organization.currency)),
                    language=str(body.get("language", organization.language)),
                ),
            )
        except ValidationError as error:
            return _validation_response(error)
        record_audit_event(
            action="administration.organization_updated",
            actor=request.user,
            organization=organization,
            object_type="Organization",
            object_id=str(organization.public_id),
            request=request,
        )
        return Response({"organization": organization_settings_payload(organization)})


class OrganizationLogoView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    required_capabilities = {
        "POST": "settings.manage",
        "DELETE": "settings.manage",
    }

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [HasCapability()]

    def get(self, request: Request):
        organization = request.tenant_context.organization
        if not organization.logo:
            return Response({"detail": t("admin.logo_not_uploaded")}, status=404)
        return FileResponse(
            organization.logo.open("rb"),
            content_type=organization.logo_content_type or "application/octet-stream",
            filename="organization-logo",
        )

    def post(self, request: Request) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": t("admin.choose_logo_file")}, status=400)
        try:
            organization = replace_organization_logo(
                context=request.tenant_context,
                upload=upload,
            )
        except ValidationError as error:
            return _validation_response(error)
        record_audit_event(
            action="administration.logo_updated",
            actor=request.user,
            organization=organization,
            object_type="Organization",
            object_id=str(organization.public_id),
            request=request,
        )
        return Response({"organization": organization_settings_payload(organization)})

    def delete(self, request: Request) -> Response:
        organization = delete_organization_logo(context=request.tenant_context)
        record_audit_event(
            action="administration.logo_deleted",
            actor=request.user,
            organization=organization,
            object_type="Organization",
            object_id=str(organization.public_id),
            request=request,
        )
        return Response({"organization": organization_settings_payload(organization)})


AUDIT_PAGE_SIZE_DEFAULT = 25
AUDIT_PAGE_SIZE_MAX = 100
# Пресеты периода вместо календаря: журнал смотрят «что было сегодня» и «что
# было за неделю», а не произвольный отрезок.
AUDIT_PERIODS = {"today": 0, "7d": 7, "30d": 30, "90d": 90}


def _audit_period_start(period: str):
    """Начало периода в часовом поясе организации, а не в UTC: «сегодня» должно
    означать сегодня у того, кто смотрит журнал."""

    if period not in AUDIT_PERIODS:
        return None
    now = django_timezone.localtime()
    start_day = (now - timedelta(days=AUDIT_PERIODS[period])).date()
    return django_timezone.make_aware(
        datetime.combine(start_day, time.min), now.tzinfo
    )


class AuditListView(APIView):
    """Журнал действий: фильтры, поиск и постраничный вывод.

    Раньше отдавались последние 50 событий без фильтров — дальше пятидесятого
    события журнала не существовало, и найти в нём что-либо было нельзя.
    """

    permission_classes = [HasCapability]
    required_capability = "audit.view"

    def get(self, request: Request) -> Response:
        organization_id = request.tenant_context.organization_id
        base = AuditEvent.objects.filter(organization_id=organization_id)
        events = base.select_related("actor")

        period = str(request.query_params.get("period", "")).strip()
        since = _audit_period_start(period)
        if since is not None:
            events = events.filter(created_at__gte=since)

        category = str(request.query_params.get("category", "")).strip()
        if category:
            # Раздел — это префикс кода действия; синонимы префиксов ищем вместе,
            # иначе «Диалоги» потеряют события, записанные как conversation.*.
            prefixes = {category} | {
                alias for alias, target in AUDIT_CATEGORY_ALIASES.items() if target == category
            }
            condition = Q()
            for prefix in prefixes:
                condition |= Q(action__startswith=f"{prefix}.")
            events = events.filter(condition)

        result = str(request.query_params.get("result", "")).strip().upper()
        if result in AUDIT_RESULT_LABELS:
            events = events.filter(result=result)

        actor = str(request.query_params.get("actor", "")).strip()
        if actor == "system":
            events = events.filter(actor__isnull=True)
        elif actor.isdigit():
            events = events.filter(actor_id=int(actor))

        query = str(request.query_params.get("q", "")).strip()
        if query:
            events = events.filter(
                Q(action__icontains=query)
                | Q(object_type__icontains=query)
                | Q(object_id__icontains=query)
                | Q(actor__full_name__icontains=query)
                | Q(actor__email__icontains=query)
            )

        try:
            page_size = int(request.query_params.get("pageSize", AUDIT_PAGE_SIZE_DEFAULT))
        except (TypeError, ValueError):
            page_size = AUDIT_PAGE_SIZE_DEFAULT
        page_size = max(1, min(page_size, AUDIT_PAGE_SIZE_MAX))
        try:
            page = int(request.query_params.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        total = events.count()
        page_count = max(1, -(-total // page_size))
        page = min(page, page_count)
        start = (page - 1) * page_size
        rows = events.order_by("-created_at", "-id")[start:start + page_size]

        return Response(
            {
                "items": [audit_event_payload(event) for event in rows],
                "page": page,
                "pageSize": page_size,
                "pageCount": page_count,
                "total": total,
                # Списки для фильтров считаем по всей организации, а не по
                # текущей выборке: иначе фильтр схлопывается до одного значения
                # и из него не выбраться.
                "filters": {
                    "categories": audit_categories(),
                    "results": [
                        {"value": key, "label": audit_result_label(key)}
                        for key in AUDIT_RESULT_LABELS
                    ],
                    "actors": _audit_actors(base),
                },
            }
        )


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
        {
            "value": str(row["actor_id"]),
            "label": row["actor__full_name"] or row["actor__email"],
        }
        for row in rows
    ]
    actors.sort(key=lambda item: str(item["label"]).lower())
    if base.filter(actor__isnull=True).exists():
        actors.append({"value": "system", "label": "Система"})
    return actors


class LaunchChecklistView(APIView):
    """Чек-лист «Запуск» (SPEC-CHATBALLS-0031 §5, дизайн-базлайн v2): три шага с
    автоотметкой по факту. Скрытие блока — предпочтение клиента (localStorage)."""

    permission_classes = [HasCapability]
    required_capability = "settings.view"

    def get(self, request: Request) -> Response:
        from chatballs.channels.models import Channel
        from chatballs.identity.models import OrganizationMembership
        from chatballs.integrations.models import Integration, IntegrationKind

        organization_id = request.tenant_context.organization_id
        agent_created = Channel.objects.filter(organization_id=organization_id).exists()
        connection_bound = Integration.objects.filter(
            organization_id=organization_id,
            kind=IntegrationKind.MESSENGER,
            channel__isnull=False,
        ).exists()
        employee_invited = (
            OrganizationMembership.objects.filter(
                organization_id=organization_id
            ).count()
            > 1
            or request.tenant_context.organization.invitations.exists()
        )
        return Response(
            {
                "agentCreated": agent_created,
                "connectionBound": connection_bound,
                "employeeInvited": employee_invited,
                "done": agent_created and connection_bound and employee_invited,
            }
        )
