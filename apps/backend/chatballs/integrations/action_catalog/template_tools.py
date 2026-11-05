"""Safe rendering, variable discovery and original library management grants."""

from dataclasses import replace

from chatballs.conversations import template_permissions as service
from chatballs.conversations.template_rendering import render_template
from chatballs.conversations.template_variables import variable_catalog
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    CONVERSATION_ID,
    IDENTIFIER,
    TEXT,
    action,
    obj,
    required,
)
from chatballs.integrations.action_catalog.template_schemas import VARIABLE
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def variables(context, values):
    return OperationResult(ResultState.COMPLETED,
        {"items": variable_catalog(context.tenant, values.get("conversation_id"))})


def render(context, values):
    return OperationResult(ResultState.COMPLETED, render_template(context.tenant,
        values["template_id"], values["conversation_id"]))


def permissions(context, values):
    return OperationResult(ResultState.COMPLETED, service.library_permissions(context.tenant))


def grant(context, values):
    return OperationResult(ResultState.COMPLETED, service.management_grant(context.tenant, values["membership_id"]))


def set_grant(context, values):
    return OperationResult(ResultState.COMPLETED, service.set_management_grant(context.tenant,
        values["membership_id"], {"granted": values["granted"]}))


for key, title, inputs, output, handler, method, suffix, view, module, scope, effect in (
    ("templates.variables.get", "native.template_variables", obj(conversation_id=replace(CONVERSATION_ID, required=False)),
        obj(items=TypeSpec("array", items=VARIABLE)), variables, "GET", "variables/", "TemplateVariablesView", "template_variable_views", "organization", Effect.READ),
    ("templates.render.post", "native.template_render", obj(template_id=IDENTIFIER, conversation_id=CONVERSATION_ID),
        obj(text=TEXT, unfilledKeys=TypeSpec("array", items=TEXT)), render, "POST", "<int:template_id>/render/", "TemplateRenderView", "template_variable_views", "conversation", Effect.READ),
    ("templates.permissions.get", "native.template_permissions", obj(),
        obj(canManageShared=BOOLEAN, canGrantSharedManagement=BOOLEAN), permissions, "GET", "permissions/", "TemplatePermissionsView", "template_permission_views", "organization", Effect.READ),
    ("templates.management_grant.get", "native.template_management_grant", obj(membership_id=IDENTIFIER),
        obj(membershipId=TypeSpec("integer"), canManageShared=BOOLEAN, granted=BOOLEAN), grant, "GET", "permissions/<int:membership_id>/", "TemplateManagementGrantView", "template_permission_views", "organization", Effect.READ),
    ("templates.management_grant.patch", "native.template_management_grant_update", obj(membership_id=IDENTIFIER, granted=required(BOOLEAN)),
        obj(membershipId=TypeSpec("integer"), canManageShared=BOOLEAN, granted=BOOLEAN), set_grant, "PATCH", "permissions/<int:membership_id>/", "TemplateManagementGrantView", "template_permission_views", "organization", Effect.UPDATE),
):
    action(key=key, title=title, input=inputs, output=output, handler=handler,
        capability="conversations.view", scope=scope, route=f"conversations/templates/{suffix}",
        view=f"chatballs.conversations.{module}.{view}", method=method, effect=effect)
