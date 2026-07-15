"""Seed a few demo orders so the sales metrics light up in local dev.

Idempotent: does nothing if the organization already has orders. Uses existing
contacts and active offers — does not invent products/prices.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from hub_platform.conversations.models import Contact
from hub_platform.identity.models import Organization
from hub_platform.orders.models import Order
from hub_platform.orders.services import OrderItemInput, create_order, mark_paid
from hub_platform.products.models import Offer
from hub_platform.tenancy.context import TenantActorKind, TenantContext
from hub_platform.tenancy.database import set_local_tenant


class Command(BaseCommand):
    help = "Seed demo orders for local development (idempotent)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--organization", required=True, help="Organization public UUID")

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        try:
            organization = Organization.objects.get(public_id=options["organization"])
        except (Organization.DoesNotExist, ValueError):
            self.stderr.write("organization not found")
            return
        context = TenantContext.for_resource(
            organization, actor_kind=TenantActorKind.SYSTEM
        )
        set_local_tenant(context)
        if Order.objects.filter(organization=organization).exists():
            self.stdout.write("orders already present — skipping")
            return
        contacts = list(Contact.objects.filter(organization=organization).order_by("id")[:6])
        offers = list(Offer.objects.filter(product__organization=organization, is_active=True).order_by("id"))
        if not contacts or not offers:
            self.stderr.write("need contacts and active offers — seed channels/catalog first")
            return

        created = 0
        for index, contact in enumerate(contacts):
            offer = offers[index % len(offers)]
            order = create_order(
                context=context,
                contact=contact,
                items=[OrderItemInput(offer_id=offer.id, quantity=1)],
            )
            if index % 3 != 0:  # часть оставляем в ожидании оплаты
                mark_paid(context=context, order=order)
            created += 1
        self.stdout.write(self.style.SUCCESS(f"seeded {created} demo orders"))
