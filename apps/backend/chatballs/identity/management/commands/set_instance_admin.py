from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from chatballs.identity.models import HumanUser


class Command(BaseCommand):
    help = (
        "Grants or revokes the installation administrator flag for an existing "
        "account. The flag controls installation-wide settings (address, mail, "
        "TURN, file storage) and is not derived from any organization role. "
        "Passwords and memberships are not touched."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--email", required=True, help="Account e-mail")
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--grant", action="store_true", help="Make the account an installation administrator")
        group.add_argument("--revoke", action="store_true", help="Remove the installation administrator flag")

    def handle(self, *args: object, **options: object) -> None:
        email = HumanUser.objects.normalize_email(str(options["email"])).lower()
        user = HumanUser.objects.filter(email__iexact=email).first()
        if user is None:
            raise CommandError(f"Account {email!r} not found")
        grant = bool(options["grant"])
        if grant and not user.is_active:
            raise CommandError(f"Account {email!r} is inactive")
        if not grant and not HumanUser.objects.filter(is_instance_admin=True, is_active=True).exclude(pk=user.pk).exists():
            raise CommandError("Cannot revoke the last active installation administrator")
        if user.is_instance_admin == grant:
            self.stdout.write(f"{email}: already {'an' if grant else 'not an'} installation administrator")
            return
        user.is_instance_admin = grant
        user.save(update_fields=["is_instance_admin"])
        self.stdout.write(self.style.SUCCESS(f"{email}: installation administrator {'granted' if grant else 'revoked'}"))
