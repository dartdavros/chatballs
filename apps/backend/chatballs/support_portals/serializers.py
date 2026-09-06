from django.conf import settings

from chatballs.support_portals.models import (
    PortalArticle,
    PortalArticleRevision,
    PortalCategory,
    SupportPortal,
    SupportPortalProduct,
)
from chatballs.integrations.models import IntegrationProvider, IntegrationStatus
from chatballs.support_portals.addressing import portal_public_url
from chatballs.support_portals.domain_services import (
    domain_verification_name,
    domain_verification_value,
)


def product_link_payload(link: SupportPortalProduct) -> dict:
    widget_key = _public_widget_key(link.support_widget, "AUTHENTICATED_PRODUCT")
    return {
        "productId": link.product_id,
        "code": link.product.code,
        "name": link.product.name,
        "supportChannelId": link.support_channel_id,
        "supportChannelCode": (
            link.support_channel.code if link.support_channel_id else None
        ),
        "supportWidgetId": link.support_widget_id,
        "supportWidgetKey": widget_key,
        "sortOrder": link.sort_order,
    }


def portal_payload(portal: SupportPortal) -> dict:
    public_url = portal_public_url(
        hosted=portal.hosted_domain,
        custom=portal.custom_domain,
        custom_verified=portal.custom_domain_verified_at is not None,
    )
    return {
        "id": portal.id,
        "publicId": str(portal.public_id),
        "slug": portal.slug,
        "hostedDomain": portal.hosted_domain,
        "customDomain": portal.custom_domain or None,
        "customDomainAddress": (
            {
                "name": portal.custom_domain,
                "type": "A",
                "value": settings.CHATBALLS_HELP_PUBLIC_IPV4,
            }
            if portal.custom_domain and settings.CHATBALLS_HELP_PUBLIC_IPV4
            else None
        ),
        "customDomainVerifiedAt": portal.custom_domain_verified_at,
        "customDomainVerification": (
            {
                "name": domain_verification_name(portal),
                "type": "TXT",
                "value": domain_verification_value(portal),
            }
            if portal.custom_domain and portal.custom_domain_verified_at is None
            else None
        ),
        "publicUrl": public_url,
        "name": portal.name,
        "defaultLocale": portal.default_locale,
        "theme": portal.theme,
        "themeScheme": portal.theme_scheme,
        "themeSettings": portal.theme_settings or {},
        "status": portal.status,
        "publishedAt": portal.published_at,
        "widgetId": portal.widget_id,
        "widgetKey": _public_widget_key(portal.widget, "ANONYMOUS"),
        "widgetChannelId": portal.widget_channel_id,
        "widgetChannelCode": _public_widget_channel_code(portal),
        "products": [product_link_payload(link) for link in portal.product_links.all()],
        "createdAt": portal.created_at,
        "updatedAt": portal.updated_at,
    }


def category_payload(
    category: PortalCategory, *, article_count: int | None = None
) -> dict:
    payload = {
        "id": category.id,
        "slug": category.slug,
        "name": category.name,
        "description": category.description,
        "parentId": category.parent_id,
        "sortOrder": category.sort_order,
    }
    if article_count is not None:
        payload["articleCount"] = article_count
    return payload


def revision_payload(revision: PortalArticleRevision, *, content: bool = True) -> dict:
    payload = {
        "id": revision.id,
        "revision": revision.revision,
        "title": revision.title,
        "summary": revision.summary,
        "createdAt": revision.created_at,
        "publishedAt": revision.published_at,
    }
    if content:
        payload["content"] = revision.content
    return payload


def article_payload(article: PortalArticle, *, revisions: bool = False) -> dict:
    latest_revision = next(iter(article.revisions.all()), None)
    payload = {
        "id": article.id,
        "slug": article.slug,
        "locale": article.locale,
        "status": article.status,
        "category": category_payload(article.category),
        "publishedRevision": (
            revision_payload(article.published_revision)
            if article.published_revision_id
            else None
        ),
        "latestRevision": (
            revision_payload(latest_revision, content=False)
            if latest_revision is not None
            else None
        ),
        "createdAt": article.created_at,
        "updatedAt": article.updated_at,
    }
    if revisions:
        payload["revisions"] = [
            revision_payload(revision) for revision in article.revisions.all()
        ]
    return payload


def public_portal_payload(portal: SupportPortal) -> dict:
    widget_key = _public_widget_key(portal.widget, "ANONYMOUS")
    return {
        "slug": portal.slug,
        "name": portal.name,
        "defaultLocale": portal.default_locale,
        "theme": portal.theme,
        "themeScheme": portal.theme_scheme,
        "themeSettings": portal.theme_settings or {},
        "webWidgetKey": widget_key,
        "webWidgetChannelCode": _public_widget_channel_code(portal),
        "products": [
            {
                "code": link.product.code,
                "name": link.product.name,
                "siteUrl": link.product.site_url,
                "supportAvailable": _public_widget_key(
                    link.support_widget,
                    "AUTHENTICATED_PRODUCT",
                ) is not None,
                "supportWidgetKey": _public_widget_key(
                    link.support_widget,
                    "AUTHENTICATED_PRODUCT",
                ),
                "supportChannelCode": (
                    link.support_channel.code if link.support_channel_id else None
                ),
            }
            for link in portal.product_links.all()
        ],
    }


def _public_widget_channel_code(portal: SupportPortal) -> str | None:
    widget = portal.widget
    if _public_widget_key(widget, "ANONYMOUS") is None:
        return None
    channel = widget.integration.channel
    if (
        channel is None
        or not channel.is_active
        or channel.requires_authenticated_product_identity
        or not channel.allow_anonymous_sessions
    ):
        return None
    available = channel.connections.filter(
        provider=IntegrationProvider.WEB,
        status=IntegrationStatus.OK,
        is_active=True,
    ).exists()
    return channel.code if available else None


def _public_widget_key(widget, expected_mode: str) -> str | None:
    if widget is None or widget.mode != expected_mode or widget.status != "PUBLISHED":
        return None
    integration = widget.integration
    channel = integration.channel
    if (
        channel is None
        or not channel.is_active
        or integration.provider != IntegrationProvider.WEB
        or integration.status != IntegrationStatus.OK
        or not integration.is_active
    ):
        return None
    return widget.public_key


def public_article_payload(article: PortalArticle, *, content: bool = True) -> dict:
    return {
        "slug": article.slug,
        "locale": article.locale,
        "category": category_payload(article.category),
        "revision": revision_payload(article.published_revision, content=content),
        "updatedAt": article.updated_at,
    }
