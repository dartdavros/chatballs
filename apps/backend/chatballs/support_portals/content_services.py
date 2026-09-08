from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.text import slugify

from chatballs.ai.indexing import reindex_portal_article
from chatballs.conversations.transports.base import guess_content_type, safe_filename
from chatballs.support_portals.content_markdown import normalize_file_links
from chatballs.support_portals.models import (
    PortalArticle,
    PortalArticleFeedback,
    PortalArticleFile,
    PortalArticleRevision,
    PortalCategory,
    SupportPortal,
)
from chatballs.support_portals.statuses import ArticleStatus, PortalStatus
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.storage import adjust_storage_usage
from chatballs.tenancy.storage_quota import (
    finalize_storage,
    release_storage,
    reserve_storage,
)

# Лимит на файл статьи — как у вложений знаний и подпись в drop-зоне редактора.
MAX_ARTICLE_FILE_BYTES = 25 * 1024 * 1024


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
    *, context: TenantContext, article: PortalArticle, data: dict, author=None
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
        content=normalize_file_links(str(data.get("content", ""))),
        created_by=author,
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


# Типы, которые файловый endpoint портала отдаёт inline: в статью их вставляют
# тегом <img> (и ссылкой на PDF), поэтому вложением их отдавать нельзя.
# Остальное — только скачиванием: тип приходит от загружающего, а страница
# открывается на домене портала.
INLINE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
        "application/pdf",
    }
)


def _clean_content_type(raw: str | None, filename: str) -> str:
    """Тип содержимого без параметров; незнакомый — угадываем по имени файла.

    Значение попадает в заголовок ответа, поэтому брать его у клиента как есть
    нельзя: параметры (``; charset=…``) и произвольные строки там не нужны.
    """
    candidate = str(raw or "").split(";")[0].strip().lower()
    if candidate in INLINE_CONTENT_TYPES:
        return candidate
    return guess_content_type(filename)


def add_article_file(
    *,
    context: TenantContext,
    article: PortalArticle,
    upload: UploadedFile,
    author=None,
) -> PortalArticleFile:
    """Загрузка файла статьи: одноимённый файл заменяется, квота учитывается."""

    ensure_portal_editable(article.portal)
    if article.status == ArticleStatus.ARCHIVED:
        raise ValidationError({"article": "Архивную статью нельзя изменять"})
    original_name = safe_filename((upload.name or "").strip(), "")
    if not original_name:
        raise ValidationError({"file": "Имя файла обязательно"})
    if upload.size and upload.size > MAX_ARTICLE_FILE_BYTES:
        raise ValidationError({"file": "Файл больше 25 МБ"})
    existing = article.files.filter(original_name=original_name).first()
    existing_size = existing.size if existing is not None else 0
    data = upload.read()
    reservation_key = f"portal-article-file:{article.id}:{original_name}"
    reserve_storage(
        context=context, expected_bytes=len(data), idempotency_key=reservation_key
    )
    try:
        if existing is not None:
            existing.file.delete(save=False)
            existing.delete()
            if existing_size:
                adjust_storage_usage(context=context, delta_bytes=-existing_size)
        article_file = PortalArticleFile(
            organization=context.organization,
            article=article,
            original_name=original_name,
            content_type=_clean_content_type(upload.content_type, original_name),
            size=len(data),
            uploaded_by=author,
        )
        article_file.file.save(original_name, ContentFile(data), save=True)
    except Exception:
        release_storage(context=context, idempotency_key=reservation_key)
        raise
    finalize_storage(
        context=context, idempotency_key=reservation_key, actual_bytes=len(data)
    )
    return article_file


def delete_article_file(
    *, context: TenantContext, article_file: PortalArticleFile
) -> None:
    ensure_portal_editable(article_file.article.portal)
    released_bytes = article_file.size
    article_file.file.delete(save=False)
    article_file.delete()
    if released_bytes:
        adjust_storage_usage(context=context, delta_bytes=-released_bytes)
