"""Read-only definition copies never turn credential inputs into action output."""

from copy import deepcopy

from chatballs.ai.diagnostic_redaction import DiagnosticRedactor, integration_secrets
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.integrations.execution.payloads import clean_value
from chatballs.integrations.models import Integration
from chatballs.integrations.scenarios.catalog import definition_context
from chatballs.integrations.scenarios.definition import child_lists

REDACTED = {"redacted": True}


def binding(spec, value, secrets, depth=0):
    if depth > 32 or spec is None or spec.secret:
        return dict(REDACTED)
    if isinstance(value, dict) and value.get("source") == "constant":
        result = deepcopy(value)
        result["value"] = clean_value(spec, result.get("value"), secrets)
        return result
    if isinstance(value, dict) and isinstance(value.get("source"), str):
        return clean_value(None, value, secrets)
    if isinstance(value, dict):
        from chatballs.integrations.adapters.schema import TypeSpec
        return {key: binding(spec.field(key) or (TypeSpec("json", nullable=True) if spec.open else None),
            child, secrets, depth + 1) for key, child in value.items()}
    if isinstance(value, list):
        return [binding(spec.items, child, secrets, depth + 1) for child in value]
    return clean_value(spec, value, secrets)


def safe_definition(tenant, document):
    result = deepcopy(document)
    context = definition_context(tenant.organization_id)
    secrets = integration_secrets(Integration.objects.filter(organization_id=tenant.organization_id))

    def visit(steps):
        for step in steps:
            if not isinstance(step, dict):
                continue
            schema = None
            if step.get("kind") == "action":
                schema = context.operations.get((str(step.get("connection")), step.get("target")))
            elif step.get("kind") == "call":
                schema = context.scenarios.get(str(step.get("scenario")))
            if "inputs" in step:
                step["inputs"] = binding(schema[0] if schema else None, step["inputs"], secrets)
            for _, children in child_lists(step):
                visit(children)

    visit(result.get("steps", []))
    return DiagnosticRedactor(Pseudonymizer(), secrets).clean(result)
