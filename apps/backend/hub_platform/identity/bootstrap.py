from dataclasses import dataclass

from django.db import transaction

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import (
    Department,
    EmployeeProfile,
    EmployeeRole,
    HumanUser,
    Organization,
    Product,
)


@dataclass(frozen=True)
class BootstrapResult:
    organization: Organization
    sales_department: Department
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
    sales_department, _ = Department.objects.get_or_create(
        organization=organization,
        code="sales",
        defaults={"name": "Продажи"},
    )
    for code, name in (("firepage", "FirePage"), ("foxray", "Foxray")):
        Product.objects.get_or_create(organization=organization, code=code, defaults={"name": name})

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

    EmployeeProfile.objects.get_or_create(
        user=owner,
        defaults={
            "organization": organization,
            "role": EmployeeRole.OWNER,
            "department": sales_department,
            "totp_required": True,
        },
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
        owner=owner,
        created_owner=created_owner,
    )
