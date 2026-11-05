"""Portal category actions retain tree and archive constraints."""

from functools import partial

from chatballs.integrations.action_catalog.portal_operations import invoke, portal
from chatballs.integrations.action_catalog.portal_schemas import (
    CATEGORY,
    CATEGORY_EDIT,
    CATEGORY_ID,
    ID,
    field,
    named,
)
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.adapters.contracts import Effect
from chatballs.support_portals import content_services as services
from chatballs.support_portals.selectors import category_article_counts
from chatballs.support_portals.serializers import category_payload


def listing(context, values):
    row = portal(context, values)
    counts = category_article_counts(row)
    return {"items": [category_payload(item, article_count=counts.get(item.pk, 0)) for item in row.categories.all()]}


def create(context, values):
    row = services.create_category(context=context.tenant, portal=portal(context, values), data=values)
    return {"category": category_payload(row)}


def update(context, values):
    row = portal(context, values)
    category = row.categories.get(pk=values["category_id"])
    return {"category": category_payload(services.update_category(portal=row, category=category, data=values))}


def delete(context, values):
    row = portal(context, values)
    services.delete_category(portal=row, category=row.categories.get(pk=values["category_id"]))
    return {}


for key, method, route, view, inputs, outputs, service, effect in (
    ("portals.categories.get", "GET", "", "CategoryListView", obj(portal_id=ID),
        obj(items=field("categories", "array", items=CATEGORY)), listing, Effect.READ),
    ("portals.categories.post", "POST", "", "CategoryListView",
        obj(portal_id=ID, **{**CATEGORY_EDIT, "name": required(CATEGORY_EDIT["name"])}),
        obj(category=named("category", CATEGORY)), create, Effect.CREATE),
    ("portals.category.patch", "PATCH", "<int:category_id>/", "CategoryDetailView",
        obj(portal_id=ID, category_id=CATEGORY_ID, **CATEGORY_EDIT), obj(category=named("category", CATEGORY)), update, Effect.UPDATE),
    ("portals.category.delete", "DELETE", "<int:category_id>/", "CategoryDetailView",
        obj(portal_id=ID, category_id=CATEGORY_ID), obj(), delete, Effect.DELETE),
):
    capability = "support.view" if method == "GET" else "support.operate"
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, capability=capability), capability=capability, scope="organization",
        route=f"support/portals/<int:portal_id>/categories/{route}",
        view=f"chatballs.support_portals.content_views.{view}", method=method, effect=effect)
