from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from django.contrib.auth.password_validation import validate_password
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from hub_platform.ai.content_importer import import_ai_content
from hub_platform.ai.models import DEFAULT_AI_MODEL, AIAgent, AIAgentStatus
from hub_platform.channels.models import Channel
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import (
    Department,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.products.models import Product, ProductDepartment
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.database import tenant_atomic

from ._seed_specs import CHANNEL_SPECS, PRODUCT_SPECS, TONE


@dataclass(frozen=True)
class CoreSeedResult:
    organization: Organization
    sales_department: Department
    support_department: Department
    owner: HumanUser | None
    created_owner: bool


def _option_or_env(options: dict, option_name: str, env_name: str) -> str:
    return str(options.get(option_name) or os.environ.get(env_name, "")).strip()


@transaction.atomic
def _seed_core(*, owner_email: str, owner_password: str, owner_name: str) -> CoreSeedResult:
    organization, _ = Organization.objects.update_or_create(
        slug="edevs",
        defaults={"name": "ООО «ЭДЕВС»", "timezone": "Europe/Moscow", "currency": "RUB"},
    )
    sales_department, _ = Department.objects.update_or_create(
        organization=organization,
        code="sales",
        defaults={"name": "Продажи"},
    )
    # Отдел поддержки (SPEC-HUB-0010 §4.1): authenticated in-product чат.
    support_department, _ = Department.objects.update_or_create(
        organization=organization,
        code="support",
        defaults={"name": "Поддержка"},
    )
    for spec in PRODUCT_SPECS:
        product, _ = Product.objects.update_or_create(
            organization=organization,
            code=spec["code"],
            defaults={
                "name": spec["name"],
                "site_url": spec["site_url"],
            },
        )
        ProductDepartment.objects.get_or_create(product=product, department=sales_department)

    owner = None
    created_owner = False
    existing_owner = (
        organization.memberships.filter(role=EmployeeRole.OWNER).select_related("user").first()
    )
    if owner_email:
        normalized_email = HumanUser.objects.normalize_email(owner_email)
        owner, created_owner = HumanUser.objects.get_or_create(
            email=normalized_email,
            defaults={"full_name": owner_name, "is_staff": True, "is_superuser": True},
        )
        if created_owner:
            validate_password(owner_password, user=owner)
            owner.set_password(owner_password)
            owner.save(update_fields=["password"])
        changed_fields = []
        if owner_name and owner.full_name != owner_name:
            owner.full_name = owner_name
            changed_fields.append("full_name")
        if not owner.is_staff:
            owner.is_staff = True
            changed_fields.append("is_staff")
        if not owner.is_superuser:
            owner.is_superuser = True
            changed_fields.append("is_superuser")
        if changed_fields:
            owner.save(update_fields=changed_fields)
        OrganizationMembership.objects.update_or_create(
            user=owner,
            organization=organization,
            defaults={
                "role": EmployeeRole.OWNER,
                "position_title": "Владелец",
                # OWNER всегда на уровне компании (ADR-HUB-0027).
                "primary_department": None,
                "totp_required": False,
            },
        )
    elif existing_owner:
        owner = existing_owner.user
    else:
        raise CommandError(
            "OWNER is required for the first production seed. Set CUS_SEED_OWNER_EMAIL and "
            "CUS_SEED_OWNER_PASSWORD, or pass --owner-email and --owner-password."
        )

    record_audit_event(
        organization=organization,
        actor=owner,
        action="identity.production_seed_applied",
        object_type="Organization",
        object_id=str(organization.id),
        payload={"created_owner": created_owner, "applied_at": timezone.now().isoformat()},
    )
    return CoreSeedResult(
        organization=organization,
        sales_department=sales_department,
        support_department=support_department,
        owner=owner,
        created_owner=created_owner,
    )


def _seed_channels(*, context: TenantContext) -> tuple[int, int]:
    organization = context.organization
    created = 0
    agents_created = 0
    for spec in CHANNEL_SPECS:
        product = (
            Product.objects.get(organization=organization, code=spec["product_code"])
            if spec["product_code"]
            else None
        )
        department = Department.objects.get(organization=organization, code=spec["department"])
        # Дефолтные sales-флаги (аноним/lead/sales/checkout разрешены), если policy не задан.
        policy = spec["policy"] or {
            "requires_authenticated_product_identity": False,
            "allow_anonymous_sessions": True,
            "allow_self_reported_contact": True,
            "allow_sales_attribution": True,
            "allow_checkout_actions": True,
        }
        channel, was_created = Channel.objects.update_or_create(
            organization=organization,
            code=spec["code"],
            defaults={
                "name": spec["name"],
                "department": department,
                "product": product,
                "is_active": True,
                **policy,
            },
        )
        created += int(was_created)
        # Агент канала (ADR-HUB-0023): одна сущность, без релизов.
        if not AIAgent.objects.filter(channel=channel).exists():
            AIAgent.objects.create(
                channel=channel,
                name=f"{spec['name']} Agent",
                status=AIAgentStatus.DRAFT,
                model=DEFAULT_AI_MODEL,
                persona=spec["persona"],
                tone=TONE,
                instructions=spec["instructions"],
            )
            agents_created += 1
    return created, agents_created


class Command(BaseCommand):
    help = "Seed production Hub reference data, AI content and channel releases. Idempotent."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--owner-email", default="")
        parser.add_argument("--owner-password", default="")
        parser.add_argument("--owner-name", default="")

    def handle(self, *args: object, **options: object) -> None:
        # Seed выполняется только при первичной установке: OWNER создаётся ровно
        # однажды (см. _seed_core). На уже развёрнутой установке команда — no-op,
        # чтобы не затирать данные, изменённые через UI/API (например цены офферов).
        if OrganizationMembership.objects.filter(role=EmployeeRole.OWNER).exists():
            self.stdout.write(self.style.WARNING(
                "Installation already initialized (OWNER exists) — seed skipped."
            ))
            return

        owner_email = _option_or_env(options, "owner_email", "CUS_SEED_OWNER_EMAIL")
        owner_password = _option_or_env(options, "owner_password", "CUS_SEED_OWNER_PASSWORD")
        owner_name = _option_or_env(options, "owner_name", "CUS_SEED_OWNER_NAME")
        if (
            owner_email
            and not owner_password
            and not Organization.objects.filter(memberships__role=EmployeeRole.OWNER).exists()
        ):
            raise CommandError("CUS_SEED_OWNER_PASSWORD is required when creating the first OWNER.")

        core = _seed_core(
            owner_email=owner_email, owner_password=owner_password, owner_name=owner_name
        )
        membership = core.organization.memberships.select_related(
            "organization", "user"
        ).get(user=core.owner)
        context = TenantContext.for_membership(membership)
        with tenant_atomic(context):
            call_command(
                "seed_catalog",
                organization=str(core.organization.public_id),
                verbosity=0,
            )
            channels_created, agents_created = _seed_channels(context=context)
            from hub_platform.support.seed_support import seed_support_reference

            support_stats = seed_support_reference(context=context)
            content_result = import_ai_content(
                base_dir=Path(__file__).resolve().parents[6],
                context=context,
            )

        owner_state = "created" if core.created_owner else "ready"
        self.stdout.write(
            self.style.SUCCESS(
                "initial data seeded: "
                f"owner={owner_state}, "
                f"channels +{channels_created}, "
                f"agents +{agents_created}, "
                f"support {support_stats}, "
                f"knowledge +{content_result.knowledge_created}"
                f"/{content_result.knowledge_updated} updated, "
                f"fragments +{content_result.fragments_created}, "
                f"agents filled {content_result.agents_updated}, "
                f"skipped {content_result.skipped_sections}"
            )
        )
