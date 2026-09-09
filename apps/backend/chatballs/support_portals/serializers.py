
from chatballs.integrations.models import IntegrationProvider, IntegrationStatus
from chatballs.support_portals.addressing import portal_public_url
from chatballs.support_portals.content_markdown import normalize_file_links
from chatballs.support_portals.public_address import help_public_ipv4
from chatballs.support_portals.models import (
    PortalArticle,
    PortalArticleFile,
    PortalArticleRevision,
    PortalCategory,
    SupportPortal,
)


def portal_payload(portal: SupportPortal, *, counts: dict | None = None) -> dict:
    server_ipv4 = help_public_ipv4() if portal.custom_domain else ""
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
                "value": server_ipv4,
            }
            if portal.custom_domain and server_ipv4
            else None
        ),
        "customDomainVerifiedAt": portal.custom_domain_verified_at,
        "publicUrl": public_url,
        "name": portal.name,
        "defaultLocale": portal.default_locale,
        "theme": portal.theme,
        "themeScheme": portal.theme_scheme,
        "themeSettings": portal.theme_settings or {},
        "status": portal.status,
        "publishedAt": portal.published_at,
        "widgetId": portal.widget_id,
        "widgetKey": _public_widget_key(portal.widget),
        "widgetChannelId": portal.widget_channel_id,
        "widgetChannelCode": _public_widget_channel_code(portal),
        "createdAt": portal.created_at,
        "updatedAt": portal.updated_at,
        # Колонка «Материалы» списка порталов (кадр PT1) и подзаголовок карточки.
        # В списке счётчики приходят одним запросом, для одиночного ответа
        # считаются здесь — иначе после сохранения настроек шапка обнулилась бы.
        "categoryCount": (
            counts["categories"]
            if counts and "categories" in counts
            else portal.categories.count()
        ),
        "articleCount": (
            counts["articles"]
            if counts and "articles" in counts
            else portal.articles.count()
        ),
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
        "authorName": _author_name(revision.created_by),
    }
    if content:
        # Ссылки на файлы приводятся к относительным и на отдаче: тексты,
        # написанные до этого правила, иначе остались бы с абсолютным хостом
        # и картинки резал бы CSP портала.
        payload["content"] = normalize_file_links(revision.content)
    return payload


def article_payload(
    article: PortalArticle, *, revisions: bool = False, files: bool = False
) -> dict:
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
    # files всегда prefetch-нуты в селекторах статей: без этого счётчик
    # скрепки в списке дал бы запрос на строку.
    # Оценки посетителей: две кнопки под статьёй на портале. Автору важно
    # видеть их сумму, иначе кнопки собирают отзывы в никуда.
    votes = list(article.feedback.all())
    payload["feedback"] = {
        "helpful": sum(1 for vote in votes if vote.helpful),
        "unhelpful": sum(1 for vote in votes if not vote.helpful),
    }
    payload["fileCount"] = len(article.files.all())
    if files:
        payload["files"] = [
            article_file_payload(item) for item in article.files.all()
        ]
    if revisions:
        payload["revisions"] = [
            revision_payload(revision) for revision in article.revisions.all()
        ]
    return payload


def article_file_payload(article_file: PortalArticleFile) -> dict:
    return {
        "id": article_file.id,
        "name": article_file.original_name,
        "contentType": article_file.content_type,
        "size": article_file.size,
        # path — для вставки в Markdown (тот же origin, что и страница),
        # url — полный адрес для мест, где нужен абсолютный.
        "path": article_file.public_path(),
        "url": article_file.public_url(),
        "createdAt": article_file.created_at,
    }


def _author_name(user) -> str:
    if user is None:
        return ""
    full_name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip()
    return full_name or user.get_username()


def public_portal_payload(portal: SupportPortal) -> dict:
    widget_key = _public_widget_key(portal.widget)
    return {
        "slug": portal.slug,
        "name": portal.name,
        "defaultLocale": portal.default_locale,
        "theme": portal.theme,
        "themeScheme": portal.theme_scheme,
        "themeSettings": portal.theme_settings or {},
        "webWidgetKey": widget_key,
        "webWidgetChannelCode": _public_widget_channel_code(portal),
    }


def _public_widget_channel_code(portal: SupportPortal) -> str | None:
    widget = portal.widget
    if _public_widget_key(widget) is None:
        return None
    channel = widget.integration.channel
    if (
        channel is None
        or not channel.is_active
        or not channel.allow_anonymous_sessions
    ):
        return None
    available = channel.connections.filter(
        provider=IntegrationProvider.WEB,
        status=IntegrationStatus.OK,
        is_active=True,
    ).exists()
    return channel.code if available else None


def _public_widget_key(widget) -> str | None:
    if widget is None or widget.status != "PUBLISHED":
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
    payload = {
        "slug": article.slug,
        "locale": article.locale,
        "category": category_payload(article.category),
        "revision": revision_payload(article.published_revision, content=content),
        "updatedAt": article.updated_at,
    }
    if content:
        # Вложения статьи — всё, чего нет в самом тексте. Картинку, вставленную
        # в статью, посетитель уже видит; остальное (в том числе картинку,
        # просто прикреплённую к статье) он скачивает списком под текстом.
        body = payload["revision"]["content"]
        payload["attachments"] = [
            {
                "name": item.original_name,
                "path": item.public_path(),
                "size": item.size,
                "contentType": item.content_type,
            }
            for item in article.files.all()
            if item.public_path() not in body
        ]
    return payload
