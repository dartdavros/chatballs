"""Базовый слой: организация, группы, пользователи, участия, аудит.

Использует существующие идемпотентные хелперы (``ensure_*``).
"""

from __future__ import annotations

from hub_platform.ai.knowledge_categories import ensure_uncategorized_category
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.identity.group_models import EmployeeGroup, EmployeeGroupMember
from hub_platform.identity.models import (
    HumanUser,
    Organization,
    OrganizationMembership,
)
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

    for item in data.get("groups", []):
        group, _ = EmployeeGroup.objects.get_or_create(
            organization=organization, name=item["name"]
        )
        refs.groups[item["key"]] = group

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

        membership, _ = OrganizationMembership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={
                "role": item["role"],
                "position_title": item.get("positionTitle", ""),
                "phone": item.get("phone", ""),
            },
        )
        refs.memberships[item["key"]] = membership

        group = refs.groups.get(item.get("group", ""))
        if group is not None:
            EmployeeGroupMember.objects.get_or_create(
                organization=organization, group=group, employee=membership
            )
