"""Создание организации человеком из интерфейса.

Кнопка «Добавить организацию» в переключателе (дизайн-базлайн v2, A1) ведёт
на страницу с полями организации; тот, кто её заполнил, становится владельцем
новой организации и сразу в неё переключается. Это второй путь появления
организации рядом с платформенным провижинингом (platform.provisioning_service):
там оператор заводит организацию для чужого владельца по e-mail, здесь человек
заводит её себе.

Кто может: администратор установки и любой, у кого есть роль владельца или
администратора хотя бы в одной организации. Сотрудник, работающий только в
чате, чужую установку организациями не засевает.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils.text import slugify

from chatballs.ai.knowledge_categories import ensure_uncategorized_category
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.i18n.audience import customer_language
from chatballs.identity.administration_services import (
    OrganizationSettingsInput,
    validate_organization_settings,
)
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import membership_routes_for_user
from chatballs.tenancy.lookup import organization_route_by_slug, reserve_organization_id

MANAGER_ROLES = frozenset({EmployeeRole.OWNER, EmployeeRole.ADMIN})


@dataclass(frozen=True, slots=True)
class CreatedOrganization:
    organization: Organization
    membership: OrganizationMembership


def can_create_organization(user: HumanUser) -> bool:
    """Администратор установки или менеджер (владелец/администратор) где-либо."""

    if not user.is_active:
        return False
    if user.is_instance_admin:
        return True
    for route in membership_routes_for_user(user.id):
        with tenant_atomic(route.organization_id):
            role = (
                OrganizationMembership.objects.filter(
                    id=route.resource_id, user=user, blocked_at__isnull=True
                )
                .values_list("role", flat=True)
                .first()
            )
        if role in MANAGER_ROLES:
            return True
    return False


def unique_organization_slug(name: str) -> str:
    """Слаг из имени, уникальный среди организаций установки.

    Проверка идёт через каталог организаций: роль app без контекста строк
    организаций не видит (tenancy/0033).
    """

    base = slugify(name)[:40].strip("-") or "organization"
    candidate = base
    suffix = 2
    while organization_route_by_slug(candidate) is not None:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def create_organization(
    *, data: OrganizationSettingsInput, owner: HumanUser
) -> CreatedOrganization:
    """Создать организацию и сделать человека её владельцем — одной транзакцией.

    Порядок тот же, что у мастера первого запуска (identity.setup): id
    выделяется заранее, строка вставляется уже в контексте этого id — иначе
    роль app не увидит собственную вставку (tenancy/0033, политика 0035).
    """

    clean = validate_organization_settings(data)
    with transaction.atomic():
        organization_id = reserve_organization_id()
        with tenant_atomic(organization_id):
            organization = Organization(
                id=organization_id,
                name=clean.name,
                slug=unique_organization_slug(clean.name),
                status=OrganizationStatus.ACTIVE,
                timezone=clean.timezone,
                currency=clean.currency,
                language=clean.language,
            )
            organization.save(force_insert=True)
            ensure_uncategorized_category(organization)
            membership = OrganizationMembership.objects.create(
                user=owner,
                organization=organization,
                role=EmployeeRole.OWNER,
                # Должность — текстом на языке организации, как в провижининге.
                position_title=t("setup.owner_position", language=customer_language(organization)),
                totp_required=False,
            )
            record_audit_event(
                action="organization.created",
                actor=owner,
                organization=organization,
                object_type="Organization",
                object_id=str(organization.public_id),
                payload={"organizationName": organization.name},
            )
            enqueue_event(
                DomainEvent(
                    aggregate_type="Organization",
                    aggregate_id=str(organization.public_id),
                    event_type="organization.provisioned",
                    payload={},
                    tenant_context=TenantContext.for_resource(
                        organization,
                        actor_kind=TenantActorKind.SYSTEM,
                        actor_user=owner,
                    ),
                )
            )
    return CreatedOrganization(organization=organization, membership=membership)
