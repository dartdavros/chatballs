from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from chatballs.platform.capabilities import PLATFORM_CAPABILITIES
from chatballs.platform.models import PlatformOperator
from chatballs.platform.tokens import issue_platform_token


class Command(BaseCommand):
    help = (
        "Creates a PlatformOperator and an opaque API token. The plaintext token "
        "is printed ONCE; only its sha256 hash is stored. Store the plaintext in a "
        "secret store immediately. This is an irreversible credential operation."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--name", required=True, help="Platform operator display name"
        )
        parser.add_argument(
            "--token-name", default="default", help="Token label (default: default)"
        )
        parser.add_argument(
            "--capabilities",
            nargs="+",
            default=["platform.organizations.provision"],
            help="Platform capability codes to grant to this token",
        )

    def handle(self, *args: object, **options: object) -> None:
        name = str(options["name"]).strip()
        token_name = str(options["token_name"]).strip() or "default"
        capabilities = list(options["capabilities"])
        for code in capabilities:
            if code not in PLATFORM_CAPABILITIES:
                known = ", ".join(sorted(PLATFORM_CAPABILITIES))
                raise CommandError(
                    f"Unknown platform capability: {code}. Known: {known}"
                )
        operator = PlatformOperator.objects.create(name=name)
        _token_obj, plaintext = issue_platform_token(
            operator=operator, name=token_name, capabilities=capabilities
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created operator '{operator.name}' (id={operator.id}) "
                f"with token '{token_name}'."
            )
        )
        self.stdout.write(self.style.WARNING("Plaintext token (shown once):"))
        self.stdout.write(plaintext)
