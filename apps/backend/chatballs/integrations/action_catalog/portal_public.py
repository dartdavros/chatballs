"""Public portal operations retain publication and tenant boundaries."""

from functools import partial

from chatballs.integrations.action_catalog import portal_public_schemas as schema
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.portal_operations import invoke, portal
from chatballs.integrations.action_catalog.portal_schemas import ID, field
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.support_portals import public_queries as queries
from chatballs.support_portals.feedback_limits import allow_native_feedback


def published(context, values):
    row = portal(context, values)
    if row.status != "PUBLISHED":
        raise NativeAccessDenied("context")
    return row


def detail(context, values):
    return queries.detail(published(context, values))


def listing(context, values):
    return queries.listing(published(context, values), {**values, "direct": "1" if values.get("direct") else "0"})


def article(context, values):
    return queries.article_detail(published(context, values), values["article_slug"], values.get("locale"))


def feedback(context, values):
    row = published(context, values)
    queries.published_article(row, values["article_slug"], values.get("locale"))
    if not allow_native_feedback(context.tenant):
        raise NativeOperationRejected("conditions_unavailable")
    return queries.feedback(row, values["article_slug"], values.get("locale"), values["helpful"])


for key, method, route, view, inputs, outputs, service, effect in (
    ("portals.public.get", "GET", "", "PublicPortalDetailView", obj(portal_id=ID), schema.DETAIL, detail, Effect.READ),
    ("portals.public.articles.get", "GET", "articles/", "PublicArticleListView", schema.FILTERS, schema.PAGE, listing, Effect.READ),
    ("portals.public.article.get", "GET", "articles/<slug:article_slug>/", "PublicArticleDetailView",
        obj(**schema.TARGET), schema.ARTICLE_DETAIL, article, Effect.READ),
    ("portals.public.feedback.post", "POST", "articles/<slug:article_slug>/feedback/", "PublicArticleFeedbackView",
        obj(**schema.TARGET, helpful=field("helpful", "boolean", required=True)), obj(ok=field("ok", "boolean")), feedback, Effect.CREATE),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, capability=""), capability="", scope="organization",
        route=f"api/v1/help/{route}", view=f"chatballs.support_portals.public_views.{view}", method=method, effect=effect)
