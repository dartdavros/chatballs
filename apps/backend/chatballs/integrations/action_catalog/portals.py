"""Portal settings, status, widget selection and domain actions."""

from functools import partial

from chatballs.integrations.action_catalog import portal_schemas as schema
from chatballs.integrations.action_catalog.portal_operations import invoke, settings
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.adapters.contracts import Effect
from chatballs.support_portals import portal_commands as commands
from chatballs.support_portals import portal_queries as queries

for key, method, route, view, inputs, outputs, service, effect, execution in (
    ("portals.get", "GET", "", "PortalListView", schema.FILTERS, schema.PAGE,
        partial(settings, service=queries.listing, query=True), Effect.READ, "io"),
    ("portals.post", "POST", "", "PortalListView", obj(**{**schema.EDIT, "slug": required(schema.EDIT["slug"]),
        "name": required(schema.EDIT["name"])}), schema.OUTPUT,
        partial(settings, service=commands.create, body=True), Effect.CREATE, "io"),
    ("portals.detail.get", "GET", "<int:portal_id>/", "PortalDetailView", obj(portal_id=schema.ID), schema.OUTPUT,
        partial(settings, service=queries.detail, by_id=True), Effect.READ, "io"),
    ("portals.detail.patch", "PATCH", "<int:portal_id>/", "PortalDetailView", obj(portal_id=schema.ID, **schema.EDIT), schema.OUTPUT,
        partial(settings, service=commands.update, by_id=True, body=True), Effect.UPDATE, "io"),
    ("portals.status.post", "POST", "<int:portal_id>/status/", "PortalStatusView",
        obj(portal_id=schema.ID, status=required(schema.STATUS)), schema.OUTPUT,
        partial(settings, service=commands.status, by_id=True, body=True), Effect.UPDATE, "io"),
    ("portals.widgets.get", "GET", "<int:portal_id>/widgets/", "PortalWidgetOptionsView", obj(portal_id=schema.ID),
        obj(items=schema.field("widgets", "array", items=schema.WIDGET)),
        partial(settings, service=queries.widgets, by_id=True), Effect.READ, "local"),
    ("portals.domain.put", "PUT", "<int:portal_id>/domain/", "PortalDomainView",
        obj(portal_id=schema.ID, customDomain=schema.field("customDomain")), schema.OUTPUT,
        partial(settings, service=commands.domain, by_id=True, body=True), Effect.UPDATE, "io"),
    ("portals.domain.verify.post", "POST", "<int:portal_id>/domain/verify/", "PortalDomainVerifyView",
        obj(portal_id=schema.ID), schema.OUTPUT,
        partial(settings, service=commands.verify_domain, by_id=True), Effect.UPDATE, "io"),
):
    capability = "support.view" if method == "GET" else "support.operate"
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, capability=capability), capability=capability,
        scope="organization", route=f"support/portals/{route}",
        view=f"chatballs.support_portals.portal_views.{view}", method=method, effect=effect, execution=execution)
