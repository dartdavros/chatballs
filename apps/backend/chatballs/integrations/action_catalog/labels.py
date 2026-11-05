"""Label actions delegate to the product catalog service."""

from chatballs.conversations import label_services as service
from chatballs.integrations.action_catalog.schema import IDENTIFIER, action, obj, required
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec

NAME = TypeSpec("string", max_length=60, title_key="native.label_name")
COLOR = TypeSpec("string", max_length=20, title_key="native.label_color")
LABEL = obj(id=TypeSpec("integer"), name=NAME, color=COLOR)


def listing(context, values):
    return OperationResult(ResultState.COMPLETED,
        {"items": [service.label_payload(row) for row in service.labels_for(context.tenant)]})


def create(context, values):
    label, _ = service.create_label(context=context.tenant, name=values["name"], color=values.get("color", ""))
    return OperationResult(ResultState.COMPLETED, {"label": service.label_payload(label)})


def update(context, values):
    label = service.update_label(context=context.tenant, label_id=values["label_id"],
        changes={name: values[name] for name in ("name", "color") if name in values})
    return OperationResult(ResultState.COMPLETED, {"label": service.label_payload(label)})


def delete(context, values):
    service.delete_label(context=context.tenant, label_id=values["label_id"])
    return OperationResult(ResultState.COMPLETED, {})


for key, title, inputs, outputs, handler, method, capability, suffix, view in (
    ("labels.get", "native.labels_list", obj(), obj(items=TypeSpec("array", items=LABEL)),
        listing, "GET", "conversations.view", "", "LabelListView"),
    ("labels.post", "native.labels_create", obj(name=required(NAME), color=COLOR), obj(label=LABEL),
        create, "POST", "conversations.operate", "", "LabelListView"),
    ("labels.label.patch", "native.labels_update", obj(label_id=IDENTIFIER, name=NAME, color=COLOR), obj(label=LABEL),
        update, "PATCH", "settings.manage", "<int:label_id>/", "LabelDetailView"),
    ("labels.label.delete", "native.labels_delete", obj(label_id=IDENTIFIER), obj(),
        delete, "DELETE", "settings.manage", "<int:label_id>/", "LabelDetailView"),
):
    action(key=key, title=title, input=inputs, output=outputs, handler=handler,
        capability=capability, scope="organization", route=f"conversations/labels/{suffix}",
        view=f"chatballs.conversations.catalog_views.{view}", method=method)
