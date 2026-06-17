from django.core.management.base import BaseCommand, CommandError

from hub_platform.identity.bootstrap import bootstrap_edevs_owner


class Command(BaseCommand):
    help = "Bootstraps the Edevs organization and first OWNER account."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--name", default="")

    def handle(self, *args: object, **options: object) -> None:
        if len(options["password"]) < 12:
            raise CommandError("Password must contain at least 12 characters.")
        result = bootstrap_edevs_owner(
            email=options["email"],
            password=options["password"],
            full_name=options["name"],
        )
        state = "created" if result.created_owner else "already_exists"
        self.stdout.write(
            self.style.SUCCESS(
                f"OWNER {state}: {result.owner.email}; org={result.organization.slug}; department={result.sales_department.code}"
            )
        )
