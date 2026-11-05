"""Skill actions retain revision checks, request receipts and template safety."""

from functools import partial

from chatballs.ai import skills_preview_service as preview
from chatballs.ai import skills_queries as queries
from chatballs.ai import skills_service as commands
from chatballs.ai.skills_validation import SkillError
from chatballs.integrations.action_catalog import skill_schemas as schema
from chatballs.integrations.action_catalog.contracts import (
    NativeAccessDenied,
    NativeOperationRejected,
)
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.action_catalog.serialization import json_data
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.tenancy.database import tenant_atomic


def invoke(context, values, *, service):
    with tenant_atomic(context.tenant):
        try:
            queries.require_manager(context.tenant)
            result = service(context.tenant, values)
        except SkillError as error:
            if error.status_code in (403, 404):
                raise NativeAccessDenied("context") from None
            raise NativeOperationRejected("arguments") from None
    return OperationResult(ResultState.COMPLETED, json_data(result))


def detail(context, values):
    return {"skill": queries.skill_payload(queries.load(context, values["skill_id"]), full=True)}


def save(context, values):
    skill, _ = commands.save_configuration(context=context, raw=values["configuration"],
        request_id=values["requestId"], public_id=values.get("skill_id"), revision=values.get("expectedRevision"))
    return {"skill": queries.skill_payload(skill, full=True)}


def delete(context, values):
    commands.delete_configuration(context=context, public_id=values["skill_id"], revision=values["expectedRevision"])
    return {}


def deletion(context, values):
    return {"skill": queries.skill_payload(queries.load(context, values["skill_id"])), "confirmationRequired": True}


def assignment(context, values, *, enabled):
    skill = commands.set_assignment(context=context, public_id=values["skill_id"],
        agent_id=values["agent_id"], revision=values["expectedRevision"], enabled=enabled)
    return {"skill": queries.skill_payload(skill)}


def draft(context, values, *, render):
    return (preview.preview if render else preview.validate)(context, values, values.get("skill_id"))


for key, method, route, view, inputs, outputs, service, effect in (
    ("skills.get", "GET", "", "SkillListView", schema.FILTERS, schema.PAGE, queries.listing, Effect.READ),
    ("skills.post", "POST", "", "SkillListView", obj(**schema.SAVE), schema.OUTPUT, save, Effect.CREATE),
    ("skills.detail.get", "GET", "<uuid:skill_id>/", "SkillDetailView", obj(skill_id=schema.ID), schema.OUTPUT, detail, Effect.READ),
    ("skills.detail.put", "PUT", "<uuid:skill_id>/", "SkillDetailView", obj(skill_id=schema.ID, expectedRevision=schema.REVISION, **schema.SAVE), schema.OUTPUT, save, Effect.UPDATE),
    ("skills.detail.delete", "DELETE", "<uuid:skill_id>/", "SkillDetailView", obj(skill_id=schema.ID, expectedRevision=schema.REVISION), obj(), delete, Effect.DELETE),
    ("skills.deletion.get", "GET", "<uuid:skill_id>/deletion/", "SkillDeletionView", obj(skill_id=schema.ID), obj(skill=schema.named("skill", schema.SUMMARY), confirmationRequired=schema.field("confirmationRequired", "boolean")), deletion, Effect.READ),
    ("skills.assignment.put", "PUT", "<uuid:skill_id>/agents/<int:agent_id>/", "SkillAssignmentView", obj(skill_id=schema.ID, agent_id=schema.field("agent", "integer", required=True), expectedRevision=schema.REVISION), schema.OUTPUT, partial(assignment, enabled=True), Effect.UPDATE),
    ("skills.assignment.delete", "DELETE", "<uuid:skill_id>/agents/<int:agent_id>/", "SkillAssignmentView", obj(skill_id=schema.ID, agent_id=schema.field("agent", "integer", required=True), expectedRevision=schema.REVISION), schema.OUTPUT, partial(assignment, enabled=False), Effect.DELETE),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service), capability="ai.manage", scope="organization",
        route=f"skills/{route}", view=f"chatballs.ai.skills_views.{view}", method=method, effect=effect)

for existing in (False, True):
    for render in (False, True):
        verb = "preview" if render else "validate"
        key = f"skills.{('detail.' if existing else '')}{verb}.post"
        inputs = dict((schema.PREVIEW if render else schema.VALIDATE).properties)
        if existing:
            inputs["skill_id"] = schema.ID
        action(key=key, title=f"native.{key}", input=obj(**inputs),
            output=schema.RENDERED if render else obj(valid=schema.field("valid", "boolean")),
            handler=partial(invoke, service=partial(draft, render=render)),
            capability="ai.manage", scope="organization", effect=Effect.READ, method="POST",
            route=f"skills/{('<uuid:skill_id>/' if existing else '')}{verb}/",
            view=f"chatballs.ai.skills_preview.Skill{'Preview' if render else 'Validation'}View")

action(key="skills.basis.get", title="native.skills.basis.get", input=obj(),
    output=obj(basisId=schema.field("basisId"), configuration=schema.named("configuration", schema.CONFIGURATION)),
    handler=partial(invoke, service=lambda tenant, _: preview.basis(tenant)), capability="ai.manage",
    scope="organization", effect=Effect.READ, method="GET", route="skills/bases/orders/",
    view="chatballs.ai.skills_preview.SkillBasisView")
