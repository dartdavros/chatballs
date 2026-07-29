#!/usr/bin/env python3
"""Local-only, credential-safe demo importer for the FoxRay support portal."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


SEED_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SEED_DIR / "support_portal.json"


def require_local_environment() -> None:
    if (
        os.environ.get("CUS_ENV") != "local"
        or os.environ.get("CUSTOCRM_LOCAL_SEED") != "1"
    ):
        raise SystemExit(
            "Support portal seed is available only through compose.dev.yaml "
            "with CUS_ENV=local."
        )


def load_manifest() -> dict:
    with MANIFEST_PATH.open(encoding="utf-8") as stream:
        manifest = json.load(stream)
    if manifest.get("schemaVersion") != 1:
        raise SystemExit("Unsupported support portal seed manifest version.")
    return manifest


def update_fields(instance, values: dict) -> None:
    changed = []
    for field, value in values.items():
        if getattr(instance, field) != value:
            setattr(instance, field, value)
            changed.append(field)
    if changed:
        instance.full_clean()
        if any(field.name == "updated_at" for field in instance._meta.fields):
            changed.append("updated_at")
        instance.save(update_fields=changed)


def run() -> None:
    require_local_environment()
    sys.path.insert(0, "/app/apps/backend")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hub_backend.settings")

    import django

    django.setup()

    from django.db import transaction
    from django.utils import timezone

    from hub_platform.channels.models import Channel
    from hub_platform.identity.models import Department, Organization
    from hub_platform.integrations.models import (
        Integration,
        IntegrationKind,
        IntegrationProvider,
        IntegrationStatus,
    )
    from hub_platform.products.models import Product
    from hub_platform.support_portals.addressing import hosted_domain
    from hub_platform.support_portals.models import (
        PortalArticle,
        PortalArticleRevision,
        PortalCategory,
        SupportPortal,
        SupportPortalProduct,
    )
    from hub_platform.support_portals.statuses import ArticleStatus, PortalStatus

    manifest = load_manifest()
    portal_data = manifest["portal"]
    widget_data = manifest["widget"]
    now = timezone.now()

    with transaction.atomic():
        organization = Organization.objects.get(slug=manifest["organization"])
        department = Department.objects.get(
            organization=organization,
            code="support",
        )
        product = Product.objects.get(
            organization=organization,
            code=portal_data["product"],
        )

        channel, _ = Channel.objects.get_or_create(
            organization=organization,
            code=widget_data["channel"],
            defaults={
                "name": widget_data["channelName"],
                "department": department,
                "product": product,
            },
        )
        update_fields(
            channel,
            {
                "name": widget_data["channelName"],
                "department": department,
                "product": product,
                "is_active": True,
                "requires_authenticated_product_identity": False,
                "allow_anonymous_sessions": True,
                "allow_self_reported_contact": True,
                "allow_sales_attribution": False,
                "allow_checkout_actions": False,
            },
        )

        integration, _ = Integration.objects.get_or_create(
            organization=organization,
            provider=IntegrationProvider.WEB,
            name=widget_data["integrationName"],
            defaults={"kind": IntegrationKind.MESSENGER},
        )
        update_fields(
            integration,
            {
                "kind": IntegrationKind.MESSENGER,
                "channel": channel,
                "config": widget_data["config"],
                "status": IntegrationStatus.OK,
                "is_active": True,
                "last_error": "",
            },
        )

        portal, _ = SupportPortal.objects.get_or_create(
            slug=portal_data["slug"],
            defaults={
                "organization": organization,
                "department": department,
                "hosted_domain": hosted_domain(portal_data["slug"]),
                "name": portal_data["name"],
                "default_locale": portal_data["locale"],
            },
        )
        update_fields(
            portal,
            {
                "department": department,
                "hosted_domain": hosted_domain(portal_data["slug"]),
                "name": portal_data["name"],
                "default_locale": portal_data["locale"],
                "widget_channel": channel,
                "status": PortalStatus.PUBLISHED,
                "published_at": portal.published_at or now,
            },
        )

        authenticated_channel = Channel.objects.filter(
            organization=organization,
            code=portal_data["authenticatedSupportChannel"],
            product=product,
            department=department,
            requires_authenticated_product_identity=True,
            allow_anonymous_sessions=False,
        ).first()
        product_link, _ = SupportPortalProduct.objects.get_or_create(
            organization=organization,
            portal=portal,
            product=product,
            defaults={"support_channel": authenticated_channel},
        )
        if product_link.support_channel_id != getattr(
            authenticated_channel,
            "id",
            None,
        ):
            product_link.support_channel = authenticated_channel
            product_link.full_clean()
            product_link.save(update_fields=["support_channel"])

        categories = {}
        for item in manifest["categories"]:
            category, _ = PortalCategory.objects.get_or_create(
                organization=organization,
                portal=portal,
                slug=item["slug"],
                defaults={"name": item["name"]},
            )
            update_fields(
                category,
                {
                    "name": item["name"],
                    "description": item["description"],
                    "sort_order": item["sortOrder"],
                },
            )
            categories[item["slug"]] = category

        for item in manifest["articles"]:
            article, _ = PortalArticle.objects.get_or_create(
                organization=organization,
                portal=portal,
                locale=portal_data["locale"],
                slug=item["slug"],
                defaults={"category": categories[item["category"]]},
            )
            category = categories[item["category"]]
            latest = article.revisions.order_by("-revision").first()
            revision_content = (
                item["title"],
                item["summary"],
                item["content"],
            )
            if latest is None or (
                latest.title,
                latest.summary,
                latest.content,
            ) != revision_content:
                latest = PortalArticleRevision.objects.create(
                    organization=organization,
                    article=article,
                    revision=(latest.revision + 1) if latest else 1,
                    title=item["title"],
                    summary=item["summary"],
                    content=item["content"],
                    published_at=now,
                )
            elif latest.published_at is None:
                latest.published_at = now
                latest.save(update_fields=["published_at"])

            article.category = category
            article.status = ArticleStatus.PUBLISHED
            article.published_revision = latest
            article.full_clean()
            article.save(
                update_fields=[
                    "category",
                    "status",
                    "published_revision",
                    "updated_at",
                ]
            )

    print(
        json.dumps(
            {
                "organization": organization.slug,
                "portal": portal.slug,
                "url": f"http://{portal.hosted_domain}/",
                "widgetChannel": channel.code,
                "categories": len(categories),
                "articles": len(manifest["articles"]),
                "idempotent": True,
                "credentialsChanged": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    run()
