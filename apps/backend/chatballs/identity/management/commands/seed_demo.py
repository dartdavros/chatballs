"""Демо-данные «Ателье Норд» из командной строки (для разработки и CI).

Штатный путь — мастер первого запуска и карточка «Демо-данные» в «Настройках».
Команда делает то же самое синхронно: ``--apply`` ставит набор в организацию
по slug, ``--remove`` удаляет его по реестру. Без флагов — сухой прогон.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed import service
from chatballs.identity.models import Organization
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic


class Command(BaseCommand):
    help = "Installs or removes the «Ателье Норд» demo dataset for an organization."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="Organization slug")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--apply", action="store_true", help="Install the demo dataset")
        group.add_argument("--remove", action="store_true", help="Remove the installed demo dataset")

    def handle(self, *args: object, **options: object) -> None:
        try:
            organization = Organization.objects.get(slug=options["organization"])
        except Organization.DoesNotExist as error:
            raise CommandError(f"Organization {options['organization']!r} not found") from error
        context = TenantContext.for_resource(organization, actor_kind=TenantActorKind.SYSTEM)

        if not options["apply"] and not options["remove"]:
            status = service.demo_status(organization)
            self.stdout.write(
                self.style.WARNING(
                    f"Dry-run: demo dataset for «{organization.name}» is {status['status']} "
                    f"({status['recordsCount']} records). Pass --apply or --remove."
                )
            )
            return

        with tenant_atomic(context):
            dataset = DemoDataset.objects.select_for_update().filter(organization=organization).first()
            if options["apply"]:
                if dataset is None:
                    dataset = DemoDataset.objects.create(
                        organization=organization, status=DemoDatasetStatus.INSTALLING
                    )
                elif dataset.status == DemoDatasetStatus.INSTALLED:
                    raise CommandError("Demo dataset is already installed; remove it first")
                else:
                    dataset.status = DemoDatasetStatus.INSTALLING
                    dataset.save(update_fields=["status"])
                dataset = service.install(context=context, dataset=dataset)
                if dataset.status != DemoDatasetStatus.INSTALLED:
                    raise CommandError(f"Demo install failed: {dataset.error}")
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Demo installed for «{organization.name}»: {dataset.records_count} records"
                    )
                )
            else:
                if dataset is None:
                    raise CommandError("Demo dataset is not installed")
                service.remove(context=context, dataset=dataset)
                self.stdout.write(self.style.SUCCESS(f"Demo removed for «{organization.name}»"))
