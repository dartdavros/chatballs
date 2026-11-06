"""Copy installed presets once. Adapter updates never write tenant definitions."""

from copy import deepcopy

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.template_labels import label_target
from chatballs.integrations.models import Integration
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.services import save_definition
from chatballs.tenancy.database import tenant_atomic


def _bindings(value, parameters=None):
    if isinstance(value, dict):
        if isinstance(value.get("source"), str):
            result = deepcopy(value)
            if result["source"] == "input":
                title = result.pop("title_key", "")
                if parameters is not None:
                    parameters[result["name"]] = {"type": "string", "required": True, "title": t(title) if title else result["name"]}
            if result["source"] == "parameter":
                # Unconfigured optional fields are omitted, never invalid nulls.
                return None
            if "field" in result:
                result["path"] = result.pop("field")
            return result
        return {key: bound for key, child in value.items() if (bound := _bindings(child, parameters)) is not None}
    if isinstance(value, list):
        return [_bindings(child, parameters) for child in value]
    return {"source": "constant", "value": value}


def copy_preset(*, tenant, connection_id, key):
    with tenant_atomic(tenant):
        connection = Integration.objects.select_related("service_settings").get(
            organization_id=tenant.organization_id, pk=connection_id,
        )
        settings = connection.service_settings
        adapter = default_registry().adapter(settings.adapter_key)
        preset = next((p for p in adapter.templates if p.key == key), None) if adapter else None
        if preset is None or adapter.contract_version != settings.adapter_version:
            raise ValidationError({"preset": t("scenarios.invalid_reference")})
        if preset.definition is not None:
            document = canonical_document(preset, connection.pk)
            return _save_copy(tenant, document, preset, adapter, t(preset.title_key))
        document = empty_definition()
        document["parameters"] = {"type": "object", "properties": {}}
        document["triggers"] = [{"id": f"trigger{i}", **deepcopy(trigger)} for i, trigger in enumerate(preset.triggers)]
        conditions = deepcopy(list(preset.conditions))
        for condition in conditions:
            if condition.get("kind") in {"no_link", "has_link"}:
                condition["connection"] = str(connection.pk)
        document["conditions"]["items"] = conditions
        document["steps"] = [
            {"id": step.id, "kind": "action", "name": t(step.title_key), "target": step.target,
             "connection": str(connection.pk) if step.target.startswith("service:") else "chatballs",
             "inputs": _bindings(step.inputs, document["parameters"]["properties"]), "onError": "stop"}
            for step in preset.steps
        ]
        for step in document["steps"]:
            if step["target"] == "chatballs:entity_link.create":
                step["inputs"]["connection"] = {"source": "constant", "value": connection.pk}
        return _save_copy(tenant, document, preset, adapter, t(preset.title_key))


def _save_copy(tenant, document, preset, adapter, name):
    copied, issues = save_definition(tenant=tenant, name=name, document=document)
    copied.origin_adapter = adapter.key
    copied.origin_key = preset.key
    copied.origin_version = preset.version
    copied.save(update_fields=["origin_adapter", "origin_key", "origin_version"])
    return copied, issues


def canonical_document(preset, connection_id):
    document = deepcopy(preset.definition)
    _assign_connection(document, str(connection_id))
    for path, title_key in preset.labels:
        node, field = label_target(document, path)
        node[field] = t(title_key)
    return document


def _assign_connection(document, connection):
    from chatballs.integrations.scenarios.definition import child_lists
    def assign(item):
        if item.get("connection") == "self":
            item["connection"] = connection
    def visit(steps):
        for step in steps:
            assign(step)
            conditions(step.get("condition", {}))
            if step.get("target") == "chatballs:entity_link.create":
                binding = step.get("inputs", {}).get("connection", {})
                if binding == {"source": "constant", "value": "self"}:
                    binding["value"] = int(connection)
            for _key, children in child_lists(step):
                visit(children)
    def conditions(group):
        for condition in group.get("items", []):
            if condition.get("kind") in {"no_link", "has_link"}:
                assign(condition)
    visit(document["steps"])
    conditions(document["conditions"])
    for trigger in document["triggers"]:
        assign(trigger)
    for pair in document["synchronization"]:
        assign(pair["left"])
        assign(pair["right"])
