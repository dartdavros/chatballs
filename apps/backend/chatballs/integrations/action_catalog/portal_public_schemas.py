"""Published portal content contracts."""

from chatballs.integrations.action_catalog.portal_content_schemas import REVISION
from chatballs.integrations.action_catalog.portal_schemas import CATEGORY, EDIT, ID, field, named
from chatballs.integrations.action_catalog.schema import obj

PORTAL = obj(**{key: spec for key, spec in EDIT.items() if key not in {"widgetId", "widgetChannelId"}},
    webWidgetKey=field("widgetKey", nullable=True), webWidgetChannelCode=field("agentCode", nullable=True))
DETAIL = obj(portal=named("portal", PORTAL), categories=field("categories", "array", items=CATEGORY))
ARTICLE = obj(slug=field("slug"), locale=field("locale"), category=named("category", CATEGORY),
    revision=named("revision", REVISION), updatedAt=field("updatedAt", "datetime"),
    attachments=field("files", "array", items=obj(name=field("name"), path=field("path"),
        size=field("size", "integer"), contentType=field("contentType"))))
ARTICLE_DETAIL = obj(article=named("article", obj(**dict(ARTICLE.properties),
    relatedArticles=field("relatedArticles", "array", items=ARTICLE))))
PAGE = obj(items=field("articles", "array", items=ARTICLE),
    pagination=named("pagination", obj(limit=field("limit", "integer"), offset=field("offset", "integer"),
        total=field("total", "integer"), hasMore=field("hasMore", "boolean"))))
TARGET = dict(portal_id=ID, article_slug=field("slug", required=True), locale=field("locale"))
FILTERS = obj(portal_id=ID, locale=field("locale"), category=field("categorySlug"),
    q=field("search"), direct=field("direct", "boolean"), limit=field("limit", "integer"), offset=field("offset", "integer"))
