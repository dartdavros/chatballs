"""Article lifecycle actions call the published-content domain services."""

from functools import partial

from chatballs.api.pagination import page_payload, paginate
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.action_catalog import portal_content_schemas as schema
from chatballs.integrations.action_catalog.portal_operations import (
    article,
    invoke,
    parameters,
    portal,
)
from chatballs.integrations.action_catalog.portal_schemas import ID, field, named
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.adapters.contracts import Effect
from chatballs.support_portals import content_services as services
from chatballs.support_portals.article_import import import_articles
from chatballs.support_portals.selectors import portal_articles_queryset
from chatballs.support_portals.serializers import article_payload, revision_payload


def listing(context, values):
    params = parameters(values)
    return page_payload(paginate(portal_articles_queryset(portal(context, values), params), params,
        default_size=25), article_payload)


def detail(context, values):
    return {"article": article_payload(article(context, values), revisions=True, files=True)}


def create(context, values):
    row = services.create_article(context=context.tenant, portal=portal(context, values), data=values)
    return detail(context, {**values, "article_id": row.pk})


def update(context, values):
    services.update_article(article=article(context, values), data=values)
    return detail(context, values)


def revision(context, values):
    row = services.add_revision(context=context.tenant, article=article(context, values),
        data=values, author=context.tenant.actor_user)
    return {"revision": revision_payload(row)}


def publish(context, values):
    services.publish_revision(article=article(context, values), revision_id=values["revisionId"])
    return detail(context, values)


def archive(context, values):
    services.archive_article(article(context, values))
    return detail(context, values)


def importing(context, values):
    result = import_articles(context=context.tenant, portal=portal(context, values), documents=values["articles"]).payload()
    record_audit_event(action="support_portal.articles_imported", actor=context.tenant.actor_user,
        organization=context.tenant.organization, object_type="PortalArticle", object_id="", payload=result)
    return result


TARGET = dict(portal_id=ID, article_id=schema.ARTICLE_ID)
for key, method, route, view, inputs, outputs, service, effect, execution in (
    ("portals.articles.get", "GET", "", "ArticleListView", schema.FILTERS, schema.PAGE, listing, Effect.READ, "local"),
    ("portals.articles.post", "POST", "", "ArticleListView",
        obj(portal_id=ID, **{key: required(value) if key in {"slug", "categoryId"} else value
            for key, value in schema.EDIT.items() if key not in {"sortOrder", "relatedArticleIds"}}, **schema.REVISION_FIELDS),
        schema.OUTPUT, create, Effect.CREATE, "local"),
    ("portals.article.get", "GET", "<int:article_id>/", "ArticleDetailView", obj(**TARGET), schema.OUTPUT, detail, Effect.READ, "local"),
    ("portals.article.patch", "PATCH", "<int:article_id>/", "ArticleDetailView", obj(**TARGET, **schema.EDIT), schema.OUTPUT, update, Effect.UPDATE, "local"),
    ("portals.article.revision.post", "POST", "<int:article_id>/revisions/", "ArticleRevisionListView",
        obj(**TARGET, **schema.REVISION_FIELDS), obj(revision=named("revision", schema.REVISION)), revision, Effect.CREATE, "local"),
    ("portals.article.publish.post", "POST", "<int:article_id>/publish/", "ArticlePublishView",
        obj(**TARGET, revisionId=field("revision", "integer", required=True)), schema.OUTPUT, publish, Effect.UPDATE, "io"),
    ("portals.article.archive.post", "POST", "<int:article_id>/archive/", "ArticleArchiveView",
        obj(**TARGET), schema.OUTPUT, archive, Effect.UPDATE, "io"),
    ("portals.articles.import.post", "POST", "import/", "ArticleImportView",
        schema.IMPORT, schema.IMPORT_RESULT, importing, Effect.CREATE, "local"),
):
    capability = "support.view" if method == "GET" else "support.operate"
    module = "article_import_views" if view == "ArticleImportView" else "content_views"
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, capability=capability), capability=capability, scope="organization",
        route=f"support/portals/<int:portal_id>/articles/{route}",
        view=f"chatballs.support_portals.{module}.{view}", method=method, effect=effect, execution=execution)
