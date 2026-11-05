"""Descriptors enumerate the two product taxonomies; no model comes from inputs."""

from functools import partial

from chatballs.conversations import template_taxonomy_services as service
from chatballs.conversations.template_models import ReplyTemplateCategory, ReplyTemplateTag
from chatballs.integrations.action_catalog.schema import IDENTIFIER, action, obj, required
from chatballs.integrations.action_catalog.template_schemas import SCOPE, TAXONOMY, TITLE
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def listing(context, values, *, model):
    return OperationResult(ResultState.COMPLETED, service.list_taxonomy(model, context.tenant))


def get(context, values, *, model):
    return OperationResult(ResultState.COMPLETED, service.get_taxonomy(model, context.tenant, values["item_id"]))


def create(context, values, *, model):
    return OperationResult(ResultState.COMPLETED, service.create_taxonomy(model, context.tenant, values))


def update(context, values, *, model):
    return OperationResult(ResultState.COMPLETED, service.update_taxonomy(model, context.tenant,
        values["item_id"], {key: value for key, value in values.items() if key != "item_id"}))


def delete(context, values, *, model):
    service.delete_taxonomy(model, context.tenant, values["item_id"])
    return OperationResult(ResultState.COMPLETED, {})


for plural, singular, model, view_prefix in (
    ("categories", "category", ReplyTemplateCategory, "Category"),
    ("tags", "tag", ReplyTemplateTag, "Tag"),
):
    for key, verb, inputs, output, handler, method, suffix, view in (
        (plural + ".get", "list", obj(), obj(items=TypeSpec("array", items=TAXONOMY)), listing, "GET", "", "ListView"),
        (plural + ".post", "create", obj(name=required(TITLE), scope=SCOPE), obj(item=TAXONOMY), create, "POST", "", "ListView"),
        (singular + ".get", "get", obj(item_id=IDENTIFIER), obj(item=TAXONOMY), get, "GET", "<int:item_id>/", "DetailView"),
        (singular + ".patch", "update", obj(item_id=IDENTIFIER, name=TITLE, scope=SCOPE), obj(item=TAXONOMY), update, "PATCH", "<int:item_id>/", "DetailView"),
        (singular + ".delete", "delete", obj(item_id=IDENTIFIER), obj(), delete, "DELETE", "<int:item_id>/", "DetailView"),
    ):
        action(key=f"templates.{key}", title=f"native.template_{singular}_{verb}", input=inputs, output=output,
            handler=partial(handler, model=model), capability="conversations.view", scope="organization",
            route=f"conversations/templates/{plural}/{suffix}", method=method,
            view=f"chatballs.conversations.template_taxonomy_views.{view_prefix}{view}")
