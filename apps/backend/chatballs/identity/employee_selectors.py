"""Выборка сотрудников для списка (кадры E1/E2).

Поиск, роль и группа — параметры запроса: страница приходит из базы уже
отфильтрованной, иначе фильтр видел бы только загруженную страницу.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q, QuerySet

from chatballs.identity.group_models import EmployeeGroupMember
from chatballs.identity.models import OrganizationMembership

ROLE_ANY = "all"


def employees_for(organization_id: int, params) -> QuerySet[OrganizationMembership]:
    employees = (
        # organization нужен для адреса аватара, группы — с их порядком: обе
        # связи берутся здесь, иначе payload спрашивал бы их на каждую строку.
        OrganizationMembership.objects.select_related("user", "organization")
        .prefetch_related(
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
    if role and role != ROLE_ANY:
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
