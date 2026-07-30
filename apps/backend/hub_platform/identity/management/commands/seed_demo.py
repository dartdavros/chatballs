"""Загружает полный набор демонстрационных данных организации «Северная Верфь».

Данные — выдуманные (РФ-наполнение), полностью покрывают значимые домены
системы. Источник — редактируемые JSON-манифесты в
``hub_platform/identity/demo_seed/data/``.

Идемпотентен: повторный запуск не дублирует и не затирает записи. По умолчанию
работает в режиме dry-run (ничего не пишет); запуск с ``--apply`` применяет сид.
Вне режима отладки требует явного ``--force`` (например, при установке облака).
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.orchestrator import run_demo_seed
from hub_platform.tenancy.context import TenantActorKind, TenantContext
from hub_platform.tenancy.database import tenant_atomic


class Command(BaseCommand):
    help = "Seeds the demo organization «Северная Верфь» with full fictional data."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the seed. Without it, only a dry-run summary is printed.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running outside DEBUG (e.g. cloud installation).",
        )

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "Demo seed is for local/cloud installation only. Pass --force to run outside DEBUG."
            )

        org_data = manifest.load("organization")["organization"]

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry-run: would seed demo organization «{org_data['name']}» "
                    f"({org_data['slug']}). Pass --apply to create the data."
                )
            )
            return

        context = TenantContext.for_resource(
            _resolve_organization(org_data),
            actor_kind=TenantActorKind.SYSTEM,
        )
        with tenant_atomic(context):
            refs = run_demo_seed(context)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo seed applied: "
                f"org={refs.organization.slug}; "
                f"users={len(refs.users)}; "
                f"products={len(refs.products)}; "
                f"channels={len(refs.channels)}; "
                f"conversations={len(refs.conversations)}"
            )
        )


def _resolve_organization(org_data: dict):
    """Возвращает организацию сида, создавая её, если нужно.

    ``run_demo_seed`` (foundation-загрузчик) идемпотентно донастроит её поля;
    здесь нужна только оболочка, чтобы построить TenantContext до старта.
    """
    from hub_platform.identity.models import Organization

    organization, _ = Organization.objects.get_or_create(
        slug=org_data["slug"],
        defaults={
            "name": org_data["name"],
            "timezone": org_data["timezone"],
            "currency": org_data["currency"],
        },
    )
    return organization
