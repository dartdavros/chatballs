"""Базовый слой: группы, демо-сотрудники, участия, приглашения.

Организация и её владелец не создаются — демо ставится в организацию
установщика (``context.organization``). Пароль всех демо-учёток один
(``demoPassword`` манифеста): установщик входит под любым из них.
"""

from __future__ import annotations

from datetime import timedelta

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.auth.totp_utils import _generate_totp_secret
from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.loaders.common import backdate, moment, now
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.identity.group_models import EmployeeGroup, EmployeeGroupMember
from hub_platform.identity.invitation_service import issue_invitation
from hub_platform.identity.models import HumanUser, OrganizationMembership
from hub_platform.tenancy.context import TenantContext


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("organization")
    organization = refs.organization
    current = now()

    for item in data.get("groups", []):
        group, _ = EmployeeGroup.objects.get_or_create(organization=organization, name=item["name"])
        refs.groups[item["key"]] = group

    password = data["demoPassword"]
    for item in data["accounts"]:
        _ensure_account(refs, item, password, current)

    for item in data.get("invitations", []):
        created_by = refs.memberships.get(item.get("createdBy"))
        expires_in = item.get("expiresInDays", 7)
        issued = issue_invitation(
            organization=organization,
            email=item["email"],
            role=item["role"],
            expires_at=current + timedelta(days=max(expires_in, 1)),
            created_by=created_by,
        )
        if expires_in < 0:
            # Просроченное приглашение: выдано неделю назад, срок вышел. Валидация
            # модели не даёт создать его сразу просроченным — откатываем даты.
            backdate(
                issued.invitation,
                current - timedelta(days=7),
                "created_at",
            )
            type(issued.invitation)._base_manager.filter(pk=issued.invitation.pk).update(
                expires_at=current + timedelta(days=expires_in)
            )

    record_audit_event(
        organization=organization,
        actor=refs.users.get("anna"),
        action="demo.installed_accounts",
        object_type="Organization",
        object_id=str(organization.public_id),
        payload={"accounts": len(refs.users)},
    )


def _ensure_account(refs: DemoRefs, item: dict, password: str, current) -> None:
    organization = refs.organization
    email = HumanUser.objects.normalize_email(item["email"])
    user, created = HumanUser.objects.get_or_create(
        email=email,
        defaults={
            "full_name": item["fullName"],
            "ui_theme": item.get("uiTheme", "SYSTEM"),
            "ui_accent": item.get("uiAccent", ""),
        },
    )
    if created:
        user.set_password(password)
        if item.get("totpEnabled"):
            user.totp_enabled = True
            user.totp_secret = _generate_totp_secret()
        user.save()
    refs.users[item["key"]] = user

    membership, membership_created = OrganizationMembership.objects.get_or_create(
        user=user,
        organization=organization,
        defaults={
            "role": item["role"],
            "position_title": item.get("positionTitle", ""),
            "phone": item.get("phone", ""),
            "blocked_at": current - timedelta(days=21) if item.get("blocked") else None,
        },
    )
    if membership_created:
        backdate(membership, current - timedelta(days=item.get("createdDaysAgo", 45)))
    refs.memberships[item["key"]] = membership

    for group_key in item.get("groups", []):
        group = refs.groups.get(group_key)
        if group is not None:
            EmployeeGroupMember.objects.get_or_create(
                organization=organization, group=group, employee=membership
            )

    if membership_created:
        record_audit_event(
            organization=organization,
            actor=refs.users.get("anna") or user,
            action="identity.employee_created",
            object_type="OrganizationMembership",
            object_id=str(membership.id),
            payload={"email": email, "role": item["role"], "source": "demo"},
        )
        if item.get("blocked"):
            record_audit_event(
                organization=organization,
                actor=refs.users.get("anna") or user,
                action="identity.employee_blocked",
                object_type="OrganizationMembership",
                object_id=str(membership.id),
                payload={"source": "demo"},
            )
        # Демо-сотрудники «входили в систему» — история для аудита и «последний вход».
        login_at = moment(item, current, "lastLogin") or current - timedelta(hours=3)
        if not item.get("blocked"):
            HumanUser.objects.filter(pk=user.pk).update(last_login=login_at)
            record_audit_event(
                organization=organization,
                actor=user,
                action="identity.login_succeeded",
                payload={"source": "demo"},
            )
