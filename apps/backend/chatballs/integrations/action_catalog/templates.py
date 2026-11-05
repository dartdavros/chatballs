"""Reply template operations use the same library services as HTTP."""

from chatballs.conversations import template_services as service
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import IDENTIFIER, TEXT, action, obj, required
from chatballs.integrations.action_catalog.template_schemas import IDS, SCOPE, TEMPLATE, TITLE
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def listing(context, values):
    return OperationResult(ResultState.COMPLETED, service.list_templates(context.tenant, values))


def get(context, values):
    return OperationResult(ResultState.COMPLETED, service.get_template(context.tenant, values["template_id"]))


def create(context, values):
    return OperationResult(ResultState.COMPLETED, service.create_template(context.tenant, values))


def update(context, values):
    return OperationResult(ResultState.COMPLETED, service.update_template(context.tenant, values["template_id"],
        {key: value for key, value in values.items() if key != "template_id"}))


def delete(context, values):
    service.delete_template(context.tenant, values["template_id"])
    return OperationResult(ResultState.COMPLETED, {})


for key, title, inputs, output, handler, method, suffix, view in (
    ("templates.get", "native.templates_list", obj(q=TEXT, scope=SCOPE, categoryId=TypeSpec("integer"),
        tagIds=IDS, **PAGE_INPUTS), page_of(TEMPLATE), listing, "GET", "", "ReplyTemplateListView"),
    ("templates.post", "native.templates_create", obj(title=required(TITLE), text=required(TEXT), scope=SCOPE,
        categoryId=TypeSpec("integer", nullable=True), tagIds=IDS), obj(template=TEMPLATE),
        create, "POST", "", "ReplyTemplateListView"),
    ("templates.template.get", "native.templates_get", obj(template_id=IDENTIFIER), obj(template=TEMPLATE),
        get, "GET", "<int:template_id>/", "ReplyTemplateDetailView"),
    ("templates.template.patch", "native.templates_update", obj(template_id=IDENTIFIER, title=TITLE, text=TEXT,
        scope=SCOPE, categoryId=TypeSpec("integer", nullable=True), tagIds=IDS), obj(template=TEMPLATE),
        update, "PATCH", "<int:template_id>/", "ReplyTemplateDetailView"),
    ("templates.template.delete", "native.templates_delete", obj(template_id=IDENTIFIER), obj(),
        delete, "DELETE", "<int:template_id>/", "ReplyTemplateDetailView"),
):
    action(key=key, title=title, input=inputs, output=output, handler=handler,
        capability="conversations.view", scope="organization", route=f"conversations/templates/{suffix}",
        view=f"chatballs.conversations.template_views.{view}", method=method)
