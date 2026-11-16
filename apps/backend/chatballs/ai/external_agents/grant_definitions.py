"""Explicitly acknowledged definitions; names and keys never grant access."""

import hashlib

from chatballs.ai.external_agents.json_payloads import dumps
from chatballs.ai.external_agents.template_models import ExternalAgentTemplateVersion
from chatballs.integrations.models import Integration


def reference(ref):
    return f'{ref["sourceConnectionId"]}:{ref["fieldId"]}'


def definitions(binding):
    custom, labels = {}, {}
    for source in Integration.objects.filter(
        organization_id=binding.organization_id, provider="WEB", is_active=True,
        pk__in=[ref["sourceConnectionId"] for ref in binding.custom_fields],
    ):
        for field in source.config.get("fields", []):
            if isinstance(field, dict) and field.get("id"):
                # Ordering and AI visibility cannot broaden the selected definition.
                value = {key: field[key] for key in ("id", "key", "label", "type", "options") if key in field}
                custom[f'{source.pk}:{field["id"]}'] = hashlib.sha256(dumps({
                    "generation": source.web_schema_generation, "field": value,
                }).encode()).hexdigest()
                labels[f'{source.pk}:{field["id"]}'] = {"sourceConnectionId": source.pk,
                    "sourceName": source.name, "fieldId": str(field["id"]),
                    "label": field.get("label", ""), "type": field.get("type", "string")}
    return {"custom": {reference(ref): custom.get(reference(ref)) for ref in binding.custom_fields},
            "customLabels": [labels[reference(ref)] for ref in binding.custom_fields if reference(ref) in labels],
            "templates": dict(ExternalAgentTemplateVersion.objects.filter(
                organization_id=binding.organization_id, template_id__in=binding.template_ids,
            ).values_list("template_id", "revision"))}


def stale_grants(binding):
    live, accepted = definitions(binding), binding.accepted_definitions
    return {"customFields": [ref for ref in binding.custom_fields
                             if not live["custom"].get(reference(ref)) or live["custom"][reference(ref)] !=
                             accepted.get("custom", {}).get(reference(ref))],
            "templateIds": [identifier for identifier in binding.template_ids
                            if not live["templates"].get(identifier) or live["templates"][identifier] !=
                            accepted.get("templates", {}).get(identifier)]}
