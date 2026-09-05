from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify

from chatballs.ai.indexing import reindex_portal_article
from chatballs.support_portals.models import (
    PortalArticle,
    PortalArticleFeedback,
    PortalArticleRevision,
    PortalCategory,
    SupportPortal,
)
from chatballs.support_portals.statuses import ArticleStatus, PortalStatus
from chatballs.tenancy.context import TenantContext


def create_category(
    *, context: TenantContext, portal: SupportPortal, data: dict
) -> PortalCategory:
    ensure_portal_editable(portal)
    parent = _category(portal, data.get("parentId")) if data.get("parentId") else None
    name = str(data.get("name", "")).strip()
    category = PortalCategory(
        organization=context.organization,
        portal=portal,
        parent=parent,
        slug=str(data.get("slug", "")).strip().lower() or _category_slug(portal, name),
        name=name,
        description=str(data.get("description", "")).strip(),
        sort_order=int(data.get("sortOrder", 0)),
    )
    category.full_clean()
    category.save()
    return category


def _category_slug(portal: SupportPortal, name: str) -> str:
    base = slugify(name)[:54] or "category"
    slug = base
    suffix = 2
    while portal.categories.filter(slug=slug).exists():
        slug = f"{base[: 63 - len(str(suffix)) - 1]}-{suffix}"
        suffix += 1
    return slug


def update_category(
    *, portal: SupportPortal, category: PortalCategory, data: dict
) -> PortalCategory:
    ensure_portal_editable(portal)
    category.parent = (
        _category(portal, data.get("parentId")) if data.get("parentId") else None
    )
    category.slug = str(data.get("slug", category.slug)).strip().lower()
    category.name = str(data.get("name", category.name)).strip()
    category.description = str(
        data.get("description", category.description)
    ).strip()
    category.sort_order = int(data.get("sortOrder", category.sort_order))
    category.full_clean()
    category.save()
    return category


def delete_category(*, portal: SupportPortal, category: PortalCategory) -> None:
    ensure_portal_editable(portal)
    if category.children.exists():
        raise ValidationError(
            {"category": "Сначала переместите или удалите вложенные разделы"}
        )
    if category.articles.exists():
        raise ValidationError(
            {"category": "Сначала переместите статьи из этого раздела"}
        )
    category.delete()


@transaction.atomic
def create_article(
    *, context: TenantContext, portal: SupportPortal, data: dict
) -> PortalArticle:
    ensure_portal_editable(portal)
    category = _category(portal, data.get("categoryId"))
    article = PortalArticle(
        organization=context.organization,
        portal=portal,
        category=category,
        slug=str(data.get("slug", "")).strip().lower(),
        locale=str(data.get("locale", portal.default_locale)).strip().lower(),
    )
    article.full_clean()
    article.save()
    add_revision(context=context, article=article, data=data)
    return article


def add_revision(
    *, context: TenantContext, article: PortalArticle, data: dict
) -> PortalArticleRevision:
    ensure_portal_editable(article.portal)
    if article.status == ArticleStatus.ARCHIVED:
        raise ValidationError({"article": "Архивную статью нельзя изменять"})
    last = article.revisions.aggregate(value=Max("revision"))["value"] or 0
    revision = PortalArticleRevision(
        organization=context.organization,
        article=article,
        revision=last + 1,
        title=str(data.get("title", "")).strip(),
        summary=str(data.get("summary", "")).strip(),
        content=str(data.get("content", "")),
    )
    revision.full_clean()
    revision.save()
    return revision


def update_article(
    *, article: PortalArticle, data: dict
) -> PortalArticle:
    ensure_portal_editable(article.portal)
    if article.status == ArticleStatus.ARCHIVED:
        raise ValidationError({"article": "Архивную статью нельзя изменять"})
    article.category = _category(
        article.portal, data.get("categoryId", article.category_id)
    )
    article.slug = str(data.get("slug", article.slug)).strip().lower()
    article.locale = str(data.get("locale", article.locale)).strip().lower()
    article.full_clean()
    article.save(update_fields=["category", "slug", "locale", "updated_at"])
    return article


@transaction.atomic
def publish_revision(
    *, article: PortalArticle, revision_id: int
) -> PortalArticle:
    ensure_portal_editable(article.portal)
    if article.status == ArticleStatus.ARCHIVED:
        raise ValidationError({"article": "Архивную статью нельзя публиковать"})
    try:
        revision = article.revisions.get(id=revision_id)
    except PortalArticleRevision.DoesNotExist as error:
        raise ValidationError({"revisionId": "Версия статьи не найдена"}) from error
    revision.published_at = timezone.now()
    revision.save(update_fields=["published_at"])
    article.published_revision = revision
    article.status = ArticleStatus.PUBLISHED
    article.full_clean()
    article.save(update_fields=["published_revision", "status", "updated_at"])
    # Агенты отвечают по опубликованной ревизии, поэтому индекс перестраивается
    # ровно в момент публикации (ADR-HUB-0016).
    reindex_portal_article(article)
    return article


@transaction.atomic
def archive_article(article: PortalArticle) -> PortalArticle:
    ensure_portal_editable(article.portal)
    article.status = ArticleStatus.ARCHIVED
    article.save(update_fields=["status", "updated_at"])
    # Архивная статья уходит и из выдачи агентов: фрагменты снимаются, связь с
    # агентом сохраняется — при восстановлении публикации она снова заработает.
    reindex_portal_article(article)
    return article


def record_feedback(article: PortalArticle, helpful: bool) -> None:
    PortalArticleFeedback.objects.create(
        organization=article.organization,
        article=article,
        helpful=helpful,
    )


def _category(portal: SupportPortal, category_id) -> PortalCategory:
    try:
        return portal.categories.get(id=int(category_id))
    except (PortalCategory.DoesNotExist, TypeError, ValueError) as error:
        raise ValidationError({"categoryId": "Раздел не найден"}) from error


def ensure_portal_editable(portal: SupportPortal) -> None:
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError(
            {"portal": "Восстановите портал, чтобы изменить его содержимое"}
        )
