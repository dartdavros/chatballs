"""Базовый слой: организация, отделы, пользователи, участия, доступ, аудит.

Использует существующие идемпотентные хелперы (``ensure_*``).
"""

from __future__ import annotations

from hub_platform.ai.knowledge_categories import ensure_uncategorized_category
from hub_platform.identity.access_defaults import ensure_system_assignment
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.identity.models import (
    Department,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.identity.system_departments import ensure_system_departments
from hub_platform.subscriptions.default_subscription import ensure_default_subscription
from hub_platform.tenancy.context import TenantContext


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("organization")
    org_data = data["organization"]

    organization, created = Organization.objects.get_or_create(
        slug=org_data["slug"],
        defaults={
            "name": org_data["name"],
            "timezone": org_data["timezone"],
            "currency": org_data["currency"],
        },
    )
    refs.organization = organization

    departments = ensure_system_departments(organization)
    refs.departments.update(departments)
    for item in data.get("extraDepartments", []):
        dept, _ = Department.objects.get_or_create(
            organization=organization,
            code=item["code"],
            defaults={"name": item["name"]},
        )
        refs.departments[item["code"]] = dept

    ensure_uncategorized_category(organization)
    slots = data.get("aiAgentSlots", 5)
    refs.subscription = ensure_default_subscription(organization, quantity=slots)

    _ensure_users_and_memberships(context, refs, data)

    if created:
        record_audit_event(
            organization=organization,
            actor=refs.users.get("owner"),
            action="demo.organization_created",
            object_type="Organization",
            object_id=str(organization.public_id),
            payload={"source": "demo-seed"},
        )


def _ensure_users_and_memberships(context: TenantContext, refs: DemoRefs, data: dict) -> None:
    organization = refs.organization
    owner_membership = None

    for item in data["accounts"]:
        email = HumanUser.objects.normalize_email(item["email"])
        user, user_created = HumanUser.objects.get_or_create(
            email=email,
            defaults={
                "full_name": item["fullName"],
                "is_staff": item.get("isStaff", False),
                "is_superuser": item.get("isSuperuser", False),
            },
        )
        if user_created:
            user.set_password(item["password"])
            user.save(update_fields=["password"])
        refs.users[item["key"]] = user

        role = item["role"]
        membership, _ = OrganizationMembership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={
                "role": role,
                "position_title": item.get("positionTitle", ""),
                "phone": item.get("phone", ""),
                "primary_department": refs.departments.get(item.get("department", "")),
            },
        )
        refs.memberships[item["key"]] = membership

        if role == EmployeeRole.OWNER:
            owner_membership = membership
        elif item.get("systemProfile") and owner_membership is not None:
            ensure_system_assignment(
                employee=membership,
                assigned_by=owner_membership,
                department=refs.departments[item["department"]],
                profile_name=item["systemProfile"],
            )
