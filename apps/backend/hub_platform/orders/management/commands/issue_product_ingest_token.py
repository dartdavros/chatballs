"""Issue (generate + store hash of) an order-ingest token for a product backend.

The plaintext token is printed ONCE — store it in the product backend's config.
Re-running rotates the token (invalidates the old one). Run deliberately.
"""

from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand, CommandError

from hub_platform.identity.models import Organization
from hub_platform.orders.services import hash_ingest_token
from hub_platform.products.models import Product


class Command(BaseCommand):
    help = "Generate an order-ingest token for a product (prints the token once)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("product_code")
        parser.add_argument("--organization", required=True, help="Organization public UUID")

    def handle(self, *args: object, **options: object) -> None:
        code = str(options["product_code"])
        try:
            organization = Organization.objects.get(public_id=options["organization"])
        except (Organization.DoesNotExist, ValueError) as error:
            raise CommandError("Unknown organization public UUID") from error
        product = Product.objects.filter(organization=organization, code=code).first()
        if product is None:
            raise CommandError(f"product '{code}' not found")
        token = secrets.token_urlsafe(32)
        product.ingest_token_hash = hash_ingest_token(token)
        product.save(update_fields=["ingest_token_hash", "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"ingest token for {code} (store it now, shown once):"))
        self.stdout.write(token)
