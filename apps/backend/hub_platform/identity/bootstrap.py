from dataclasses import dataclass

from django.db import transaction

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.access_defaults import ensure_system_assignment
from hub_platform.identity.models import (
    Department,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.products.models import Product, ProductDepartment


@dataclass(frozen=True)
class BootstrapResult:
    organization: Organization
    sales_department: Department
    support_department: Department
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
    sales_department, _ = Department.objects.get_or_create(
        organization=organization,
        code="sales",
        defaults={"name": "Продажи"},
    )
    # Отдел поддержки (ADR-HUB-0022, SPEC-HUB-0010 §4.1): authenticated in-product
    # чат существующих клиентов продуктов. Сосуществует с sales, identity разделены.
    support_department, _ = Department.objects.get_or_create(
        organization=organization,
        code="support",
        defaults={"name": "Поддержка"},
    )
    for code, name in (("firepage", "FirePage"), ("foxray", "Foxray")):
        product, _ = Product.objects.get_or_create(organization=organization, code=code, defaults={"name": name})
        ProductDepartment.objects.get_or_create(product=product, department=sales_department)
    # AI-агенты теперь на уровне канала обработки (ADR-HUB-0019) — см. seed_channels.

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

    owner_profile, _ = OrganizationMembership.objects.get_or_create(
        user=owner,
        organization=organization,
        defaults={
            "role": EmployeeRole.OWNER,
            "position_title": "Владелец",
            # OWNER всегда на уровне компании (ADR-HUB-0027): без основного отдела.
            "primary_department": None,
            "totp_required": False,
        },
    )
    # C07: every tenant operation requires an active subscription. Ensure the
    # bootstrapped organization has one so it is operational post-enforcement.
    from hub_platform.subscriptions.default_subscription import ensure_default_subscription

    ensure_default_subscription(organization)

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
            "position_title": "Оператор отдела продаж",
            "phone": "+7 916 245 14 02",
            "primary_department": sales_department,
        },
    )
    if not operator_profile.phone:
        operator_profile.phone = "+7 916 245 14 02"
        operator_profile.save(update_fields=["phone"])
    ensure_system_assignment(
        employee=operator_profile,
        assigned_by=owner_profile,
        department=sales_department,
        profile_name="Sales operator",
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
        sales_department=sales_department,
        support_department=support_department,
        owner=owner,
        created_owner=created_owner,
    )
