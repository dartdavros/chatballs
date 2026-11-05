"""Published portal content shared by public HTTP and native actions."""

from chatballs.support_portals.content_services import record_feedback
from chatballs.support_portals.selectors import category_article_counts, public_articles
from chatballs.support_portals.serializers import (
    category_payload,
    public_article_payload,
    public_portal_payload,
)


def detail(portal):
    counts = category_article_counts(portal, published_only=True, locale=portal.default_locale)
    return {"portal": public_portal_payload(portal), "categories": [
        category_payload(row, article_count=counts.get(row.id, 0)) for row in portal.categories.all()]}


def listing(portal, params):
    articles = public_articles(portal, locale=str(params.get("locale", portal.default_locale)),
        category=str(params.get("category", "")), query=str(params.get("q", "")).strip(),
        direct_category=params.get("direct") == "1")
    limit = min(max(int(params.get("limit", 50)), 1), 100)
    offset = max(int(params.get("offset", 0)), 0)
    total = articles.count()
    return {"items": [public_article_payload(row, content=False) for row in articles[offset:offset + limit]],
        "pagination": {"limit": limit, "offset": offset, "total": total, "hasMore": offset + limit < total}}


def published_article(portal, slug, locale=None):
    return public_articles(portal, locale=locale if locale is not None else portal.default_locale).get(slug=slug)


def article_detail(portal, slug, locale=None):
    article = published_article(portal, slug, locale)
    payload = public_article_payload(article)
    related = public_articles(portal, locale=article.locale).filter(id__in=article.related_article_ids)
    by_id = {row.id: row for row in related}
    payload["relatedArticles"] = [public_article_payload(by_id[identifier], content=False)
        for identifier in article.related_article_ids if identifier in by_id]
    return {"article": payload}


def feedback(portal, slug, locale, helpful):
    record_feedback(published_article(portal, slug, locale), helpful)
    return {"ok": True}
