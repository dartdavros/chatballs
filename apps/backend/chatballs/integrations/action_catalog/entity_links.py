"""Visible link management reuses verified search candidates and revisions."""

from functools import partial

from chatballs.integrations.action_catalog.contracts import APIEntry
from chatballs.integrations.action_catalog.run_management import field
from chatballs.integrations.action_catalog.scenarios import invoke
from chatballs.integrations.action_catalog.schema import action, enum, obj, required
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.scenarios import entity_link_management


def execute(context, values, *, service, arguments, body=False):
    context.require_conversation(values["conversation"])
    return invoke(context, values, service=service, arguments=arguments, body=body)


CONVERSATION = field("conversation", "integer", required=True)
IDENTIFIER = field("link", "integer", required=True)
LINK = obj(id=IDENTIFIER, name=field("name"), service=field("service"), revision=field("version", "integer"),
    searchable=field("searchable", "boolean"), url=field("url"))
CANDIDATES = obj(state=field("state"), items=field("items", "array", items=obj(id=field("record"), label=field("label"))))
PREFIX = "chatballs.integrations.scenarios.entity_link_views."
for key, method, route, view, inputs, outputs, service, arguments, body, extra in (
    ("entity_links.get", "GET", "entity-links/", "EntityLinksView", obj(conversation=CONVERSATION),
        obj(items=field("items", "array", items=LINK)), entity_link_management.listing, ("conversation",), False, ()),
    ("entity_links.search.get", "GET", "entity-links/<int:pk>/search/", "EntityLinkSearchView",
        obj(conversation=CONVERSATION, pk=IDENTIFIER, run=field("run", required=True)), CANDIDATES,
        entity_link_management.search_results, ("conversation", "pk", "run"), False,
        (APIEntry("integrations/entity-links/<int:pk>/", "GET", PREFIX + "EntityLinkCommandView"),)),
    ("entity_links.command.post", "POST", "entity-links/<int:pk>/", "EntityLinkCommandView",
        obj(conversation=CONVERSATION, pk=IDENTIFIER, revision=field("version", "integer", required=True),
            action=required(enum(("unlink", "replace"), "native.link_command")), searchRunId=field("run"), externalId=field("record")),
        obj(updated=field("updated", "boolean")), entity_link_management.change, ("conversation", "pk"), True, ()),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(execute, service=service, arguments=arguments, body=body),
        capability="conversations.view" if key == "entity_links.get" else "conversations.operate", scope="conversation",
        route=f"integrations/{route}", view=PREFIX + view, method=method, extra_entries=extra,
        effect=Effect.READ if method == "GET" else Effect.UPDATE)
