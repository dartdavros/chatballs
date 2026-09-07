"""Поддержка: портал помощи, статьи (опубликованные, черновик, архив, вторая
ревизия), оценки читателей, статьи у агентов."""

from __future__ import annotations

from datetime import timedelta

from django.core.files.base import ContentFile

from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate, now
from chatballs.identity.demo_seed.refs import DemoRefs
from chatballs.support_portals.content_services import (
    add_revision,
    archive_article,
    create_article,
    create_category,
    publish_revision,
    record_feedback,
)
from chatballs.support_portals.models import (
    PortalArticleFile,
    PortalCategory,
    SupportPortal,
)
from chatballs.support_portals.portal_services import (
    PortalInput,
    create_portal,
    set_portal_status,
)
from chatballs.support_portals.statuses import ArticleStatus, PortalStatus
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.storage import adjust_storage_usage


def load(context: TenantContext, refs: DemoRefs) -> None:
    data = manifest.load("support")
    current = now()
    _ensure_portal(context, refs, data.get("portal"), current)
    _link_agent_articles(refs)


def _ensure_portal(context: TenantContext, refs: DemoRefs, portal_data: dict | None, current) -> None:
    if not portal_data:
        return
    portal = SupportPortal.objects.filter(organization=refs.organization, slug=portal_data["slug"]).first()
    if portal is None:
        widget = refs.widgets.get(portal_data.get("widgetConnection"))
        portal = create_portal(
            context=context,
            data=PortalInput(
                slug=portal_data["slug"],
                name=portal_data["name"],
                default_locale=portal_data.get("locale", "ru"),
                widget_id=widget.id if widget is not None else None,
            ),
        )
        backdate(portal, current - timedelta(days=28), "created_at")

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
        article = _ensure_article(context, refs, portal, categories, item, current)
        for spec in item.get("files", []):
            _attach_article_file(context, refs, article, spec)

    target_status = portal_data.get("status", PortalStatus.PUBLISHED)
    if portal.status != target_status:
        set_portal_status(context=context, portal=portal, status=target_status)
    refs.portal = portal


def _ensure_article(
    context: TenantContext,
    refs: DemoRefs,
    portal: SupportPortal,
    categories,
    item: dict,
    current,
):
    article = portal.articles.filter(slug=item["slug"]).first()
    if article is None:
        article = create_article(
            context=context,
            portal=portal,
            data={
                "slug": item["slug"],
                "categoryId": categories[item["category"]].id,
                "locale": item.get("locale", portal.default_locale),
                "title": item["title"],
                "summary": item.get("summary", ""),
                "content": item.get("content", ""),
            },
        )
        published_at = current - timedelta(days=item.get("publishedDaysAgo", 7))
        backdate(article, published_at - timedelta(days=1), "created_at")
        first = article.revisions.order_by("revision").first()
        backdate(first, published_at - timedelta(days=1), "created_at")
        status = item.get("status", ArticleStatus.PUBLISHED)
        if status in (ArticleStatus.PUBLISHED, ArticleStatus.ARCHIVED):
            publish_revision(article=article, revision_id=first.id)
            first.refresh_from_db()
            backdate(first, published_at, "published_at")
        second = item.get("secondRevision")
        if second and status == ArticleStatus.PUBLISHED:
            revision = add_revision(
                context=context,
                article=article,
                data={
                    "title": item["title"],
                    "summary": second.get("summary", item.get("summary", "")),
                    "content": item.get("content", "") + second.get("contentAppend", ""),
                },
            )
            publish_revision(article=article, revision_id=revision.id)
            when = current - timedelta(days=second.get("daysAgo", 3))
            backdate(revision, when, "created_at", "published_at")
        for _ in range(item.get("helpfulVotes", 0)):
            record_feedback(article, helpful=True)
        for _ in range(item.get("unhelpfulVotes", 0)):
            record_feedback(article, helpful=False)
        if status == ArticleStatus.ARCHIVED:
            archive_article(article)
    refs.portal_articles[item["slug"]] = article
    return article


def _link_agent_articles(refs: DemoRefs) -> None:
    for agent_key, slugs in refs.agent_article_links.items():
        agent = refs.agents.get(agent_key)
        if agent is None:
            continue
        for slug in slugs:
            article = refs.portal_articles.get(slug)
            if article is not None and article.status == ArticleStatus.PUBLISHED:
                agent.portal_articles.add(article)


def _attach_article_file(context: TenantContext, refs: DemoRefs, article, spec) -> None:
    """Файл статьи портала: картинка или документ рядом с текстом
    (кадр PT7 дизайн-базлайна).
    """

    if isinstance(spec, str):
        spec = {"file": spec}
    filename = spec["file"]
    if article.files.filter(original_name=filename).exists():
        return
    payload = manifest.media_bytes(filename)
    suffix = filename.rsplit(".", 1)[-1].lower()
    content_type = spec.get("contentType") or {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "pdf": "application/pdf",
        "md": "text/markdown",
        "txt": "text/plain",
    }.get(suffix, "application/octet-stream")
    article_file = PortalArticleFile(
        organization=refs.organization,
        article=article,
        original_name=filename,
        content_type=content_type,
        size=len(payload),
    )
    article_file.file.save(filename, ContentFile(payload), save=True)
    adjust_storage_usage(context=context, delta_bytes=len(payload))
