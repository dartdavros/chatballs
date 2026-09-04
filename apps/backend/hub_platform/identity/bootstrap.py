from dataclasses import dataclass

from django.db import transaction

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.group_models import EmployeeGroup, EmployeeGroupMember
from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.products.models import Product


@dataclass(frozen=True)
class BootstrapResult:
    organization: Organization
    operators_group: EmployeeGroup
    support_group: EmployeeGroup
    owner: HumanUser
    created_owner: bool


@transaction.atomic
def bootstrap_edevs_owner(*, email: str, password: str, full_name: str = "") -> BootstrapResult:
    organization, _ = Organization.objects.get_or_create(
        slug="edevs",
        defaults={
            "name": "Edevs",
            "timezone": "Europe/Moscow",
            "currency": "RUB",
        },
    )
    from hub_platform.ai.knowledge_categories import ensure_uncategorized_category

    ensure_uncategorized_category(organization)
    # Группы сотрудников (ADR-HUB-0043): не обязательны для запуска, но дают
    # локальному контуру и тестам готовое разделение потоков.
    operators_group, _ = EmployeeGroup.objects.get_or_create(
        organization=organization, name="Операторы"
    )
    support_group, _ = EmployeeGroup.objects.get_or_create(
        organization=organization, name="Поддержка"
    )
    for code, name in (("firepage", "FirePage"), ("foxray", "Foxray")):
        Product.objects.get_or_create(organization=organization, code=code, defaults={"name": name})
    # Каналы обработки и их агенты (ADR-HUB-0019) создаются через API каналов.

    owner, created_owner = HumanUser.objects.get_or_create(
        email=HumanUser.objects.normalize_email(email),
        defaults={
            "full_name": full_name,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created_owner:
        owner.set_password(password)
        owner.save(update_fields=["password"])
    elif not owner.is_staff or not owner.is_superuser:
        owner.is_staff = True
        owner.is_superuser = True
        owner.save(update_fields=["is_staff", "is_superuser"])

    OrganizationMembership.objects.get_or_create(
        user=owner,
        organization=organization,
        defaults={
            "role": EmployeeRole.OWNER,
            "position_title": "Владелец",
            "totp_required": False,
        },
    )
    operator, created_operator = HumanUser.objects.get_or_create(
        email=HumanUser.objects.normalize_email("a.kotova@edevs.tech"),
        defaults={
            "full_name": "Анна Котова",
            "is_staff": False,
            "is_superuser": False,
        },
    )
    if created_operator:
        operator.set_password("Operator-Local-2026")
        operator.save(update_fields=["password"])

    operator_profile, _ = OrganizationMembership.objects.get_or_create(
        user=operator,
        organization=organization,
        defaults={
            "role": EmployeeRole.EMPLOYEE,
            "position_title": "Оператор",
            "phone": "+7 916 245 14 02",
        },
    )
    if not operator_profile.phone:
        operator_profile.phone = "+7 916 245 14 02"
        operator_profile.save(update_fields=["phone"])
    EmployeeGroupMember.objects.get_or_create(
        organization=organization,
        group=operators_group,
        employee=operator_profile,
    )

    record_audit_event(
        organization=organization,
        actor=owner,
        action="identity.owner_bootstrapped",
        object_type="HumanUser",
        object_id=str(owner.id),
        payload={"created_owner": created_owner},
    )

    return BootstrapResult(
        organization=organization,
        operators_group=operators_group,
        support_group=support_group,
        owner=owner,
        created_owner=created_owner,
    )
