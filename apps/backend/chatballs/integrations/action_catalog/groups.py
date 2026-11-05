"""Organization group actions retain the product domain checks and audit."""

from chatballs.identity import group_services as service
from chatballs.integrations.action_catalog.schema import IDENTIFIER, action, obj, required
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec

NAME = TypeSpec("string", max_length=120, title_key="native.groups.name")
COLOR = TypeSpec("string", max_length=20, title_key="native.label_color")
MEMBERS = TypeSpec("array", items=TypeSpec("integer"), title_key="native.groups.members")
GROUP = obj(id=TypeSpec("integer"), name=NAME, color=COLOR, memberIds=MEMBERS,
    memberCount=TypeSpec("integer", title_key="native.groups.member_count"),
    createdAt=TypeSpec("datetime", title_key="native.groups.created_at"))
OUTPUT = obj(group=TypeSpec("object", properties=GROUP.properties, title_key="native.groups.group"))


def listing(context, values):
    return OperationResult(ResultState.COMPLETED, service.list_groups(context.tenant))


def create(context, values):
    return OperationResult(ResultState.COMPLETED, service.create_group(context.tenant, values))


def update(context, values):
    return OperationResult(ResultState.COMPLETED,
        service.update_group(context.tenant, values["group_id"], values))


def delete(context, values):
    return OperationResult(ResultState.COMPLETED,
        service.delete_group(context.tenant, values["group_id"]))


for key, inputs, outputs, handler, method, capability, suffix, view, effect in (
    ("groups.get", obj(), obj(items=TypeSpec("array", items=GROUP)), listing, "GET",
        "employees.view", "", "GroupListView", Effect.READ),
    ("groups.post", obj(name=required(NAME), color=COLOR, memberIds=MEMBERS), OUTPUT, create, "POST",
        "groups.manage", "", "GroupListView", Effect.CREATE),
    ("groups.group.patch", obj(group_id=IDENTIFIER, name=NAME, color=COLOR, memberIds=MEMBERS),
        OUTPUT, update, "PATCH", "groups.manage", "<int:group_id>/", "GroupDetailView", Effect.UPDATE),
    ("groups.group.delete", obj(group_id=IDENTIFIER), obj(deleted=TypeSpec("boolean", title_key="native.groups.deleted")),
        delete, "DELETE", "groups.manage", "<int:group_id>/", "GroupDetailView", Effect.DELETE),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs, handler=handler,
        capability=capability, scope="organization", route=f"company/groups/{suffix}",
        view=f"chatballs.identity.group_views.{view}", method=method, effect=effect)
