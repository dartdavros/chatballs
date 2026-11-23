"""Выборка сотрудников для списка (кадры E1/E2).

Поиск, роль и группа — параметры запроса: страница приходит из базы уже
отфильтрованной, иначе фильтр видел бы только загруженную страницу.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet
from rest_framework.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.identity.group_models import EmployeeGroupMember
from chatballs.identity.models import EmployeeRole, OrganizationMembership
from chatballs.identity.work_status_codes import WorkStatus

ROLE_ANY = "all"


def employees_for(organization_id: int, params) -> QuerySet[OrganizationMembership]:
    employees = (
        # organization нужен для адреса аватара, группы — с их порядком: обе
        # связи берутся здесь, иначе payload спрашивал бы их на каждую строку.
        OrganizationMembership.objects.select_related("user", "organization")
        .prefetch_related(
            "supervision_links__group",
            Prefetch(
                "group_links",
                queryset=EmployeeGroupMember.objects.select_related("group").order_by(
                    "group__name"
                ),
            )
        )
        .filter(organization_id=organization_id)
    )
    role = params.get("role")
    status = params.get("status", ROLE_ANY)
    if status not in {ROLE_ANY, "active", "invited", "blocked", "dismissed"}:
        raise ValidationError({"status": t("admin.employee_status_invalid")})
    employees = employees.filter(dismissed_at__isnull=status != "dismissed")
    if status == "blocked":
        employees = employees.filter(blocked_at__isnull=False)
    if status in {"active", "invited"}:
        employees = employees.filter(blocked_at__isnull=True, user__is_active=True,
            user__must_change_password=status == "invited")
    work_status = params.get("workStatus")
    if work_status and work_status != ROLE_ANY:
        if work_status not in WorkStatus.values:
            raise ValidationError(t("work_status.status_invalid"))
        employees = employees.filter(work_status=work_status)
    if role and role != ROLE_ANY:
        if role not in EmployeeRole.values:
            raise ValidationError({"role": t("admin.invalid_role")})
        employees = employees.filter(role=role)
    group = params.get("group")
    if group and group != ROLE_ANY and str(group).isdigit():
        employees = employees.filter(group_links__group_id=int(group))
    query = params.get("q", "").strip()
    if query:
        employees = employees.filter(
            Q(user__full_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(position_title__icontains=query)
        )
    return employees.distinct().order_by("user__email")
