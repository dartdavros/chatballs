"""Tenant references of editor actions, separate from arbitrary adapter data."""

from chatballs.integrations.scenarios.definition import Issue


def entity_link_reference(step):
    if step.get("connection") != "chatballs" or step.get("target") != "chatballs:entity_link.create":
        return None
    inputs = step.get("inputs", {})
    if not isinstance(inputs, dict):
        return None
    connection = inputs.get("connection", {})
    entity = inputs.get("entity", {})
    if (not isinstance(connection, dict) or set(connection) != {"source", "value"}
            or connection["source"] != "constant" or type(connection["value"]) is not int
            or not isinstance(entity, dict) or set(entity) != {"source", "value"}
            or entity["source"] != "constant" or not isinstance(entity["value"], str)):
        return None
    return str(connection["value"]), entity["value"]


def check_native_references(step, context, path, issues):
    if step.get("connection") == "chatballs" and step.get("target") == "chatballs:webchat.first_reply":
        binding = step.get("inputs", {}).get("instruction", {})
        if (not isinstance(binding, dict) or set(binding) != {"source", "value"}
                or binding.get("source") != "constant" or not isinstance(binding.get("value"), str)):
            issues.append(Issue(f"{path}.inputs.instruction", "binding"))
    if step.get("connection") == "chatballs" and step.get("target") == "chatballs:entity_link.create":
        ref = entity_link_reference(step)
        if ref is None or ref[0] not in context.connections or ref not in context.entities:
            issues.append(Issue(f"{path}.inputs.connection", "reference"))
