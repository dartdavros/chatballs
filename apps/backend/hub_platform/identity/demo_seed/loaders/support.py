"""Поддержка: контракты, снимки идентичности, портал, статьи и ревизии."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from hub_platform.identity.demo_seed import manifest
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.support.models import (
    ContractStatus,
    ProductSupportContract,
    SupportIdentitySnapshot,
)
from hub_platform.support_portals.content_services import (
    create_article,
    create_category,
    ensure_portal_editable,
    publish_revision,
    record_feedback,
)
from hub_platform.support_portals.models import (
    PortalCategory,
    SupportPortal,
    SupportPortalProduct,
)
from hub_platform.support_portals.statuses import ArticleStatus, PortalStatus
from hub_platform.tenancy.context import TenantContext


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("support")
    _ensure_contracts(refs, data.get("contracts", []))
    _ensure_snapshots(refs, data.get("identitySnapshots", []))
    _ensure_portal(context, refs, data.get("portal"))


def _ensure_contracts(refs: DemoRefs, items: list[dict]) -> None:
    for item in items:
        contract, _ = ProductSupportContract.objects.get_or_create(
            organization=refs.organization,
            code=item["code"],
            defaults={
                "product": refs.products[item["product"]],
                "version": item["version"],
                "status": item.get("status", ContractStatus.ACTIVE),
            },
        )
        refs.support_contracts[item["key"]] = contract


def _ensure_snapshots(refs: DemoRefs, items: list[dict]) -> None:
    now = timezone.now()
    for item in items:
        contract = refs.support_contracts[item["contract"]]
        snapshot, _ = SupportIdentitySnapshot.objects.get_or_create(
            organization=refs.organization,
            contract=contract,
            subject_key=item["subjectKey"],
            defaults={
                "product": contract.product,
                "contract_code": contract.code,
                "account_key": item.get("accountKey"),
                "display_name": item.get("displayName", ""),
                "display_email": item.get("displayEmail", ""),
                "payload_json": item.get("payload", {}),
                "operator_context_json": item.get("operatorContext", {}),
                "ai_context_json": item.get("aiContext", {}),
                "search_text": item.get("searchText", ""),
                "token_issued_at": now - timedelta(days=item.get("issuedDaysAgo", 1)),
                "token_expires_at": now + timedelta(days=item.get("expiresInDays", 30)),
            },
        )
        refs.identity_snapshots[item["key"]] = snapshot


def _ensure_portal(context: TenantContext, refs: DemoRefs, portal_data: dict | None) -> None:
    if not portal_data:
        return
    organization = refs.organization

    portal, portal_created = SupportPortal.objects.get_or_create(
        slug=portal_data["slug"],
        defaults={
            "organization": organization,
            "name": portal_data["name"],
            "default_locale": portal_data.get("locale", "ru"),
            "status": portal_data.get("status", PortalStatus.PUBLISHED),
            "widget_channel": refs.channels.get(portal_data.get("widgetChannel")),
        },
    )
    if portal_created and portal.status == PortalStatus.PUBLISHED:
        portal.published_at = timezone.now()
        portal.save(update_fields=["published_at"])
    ensure_portal_editable(portal)

    for item in portal_data.get("products", []):
        product = refs.products[item]
        support_channel = refs.channels.get(f"{item}-support")
        SupportPortalProduct.objects.get_or_create(
            portal=portal,
            product=product,
            defaults={"support_channel": support_channel},
        )

    categories: dict[str, PortalCategory] = {}
    for item in portal_data.get("categories", []):
        category = PortalCategory.objects.filter(portal=portal, slug=item["slug"]).first()
        if category is None:
            category = create_category(
                context=context,
                portal=portal,
                data={
                    "slug": item["slug"],
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "sortOrder": item.get("sortOrder", 0),
                },
            )
        categories[item["slug"]] = category

    for item in portal_data.get("articles", []):
        _ensure_article(context, portal, categories, item)


def _ensure_article(
    context: TenantContext,
    portal: SupportPortal,
    categories: dict[str, PortalCategory],
    item: dict,
) -> None:
    existing = portal.articles.filter(slug=item["slug"]).first()
    if existing is not None and existing.revisions.exists():
        return  # статья уже создана — идемпотентность
    data = {
        "slug": item["slug"],
        "categoryId": categories[item["category"]].id,
        "locale": item.get("locale", portal.default_locale),
        "title": item["title"],
        "summary": item.get("summary", ""),
        "content": item.get("content", ""),
    }
    article = create_article(context=context, portal=portal, data=data)
    if item.get("status", ArticleStatus.PUBLISHED) == ArticleStatus.PUBLISHED:
        latest_revision = article.revisions.order_by("-revision").first()
        if latest_revision is not None:
            publish_revision(article=article, revision_id=latest_revision.id)
    for _ in range(item.get("helpfulVotes", 0)):
        record_feedback(article, helpful=True)
