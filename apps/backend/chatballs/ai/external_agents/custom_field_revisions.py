"""The export policy binds live definitions and durable source generations."""

import hashlib

from chatballs.ai.external_agents.json_payloads import dumps
from chatballs.integrations.models import Integration


def sources(binding):
    identifiers = {ref["sourceConnectionId"] for ref in binding.custom_fields}
    return Integration.objects.filter(
        organization_id=binding.organization_id, pk__in=identifiers, provider="WEB",
    ).order_by("pk")


def fingerprint(binding):
    policy = {"standard": sorted(binding.standard_fields),
              "custom": sorted(binding.custom_fields,
                               key=lambda ref: (ref["sourceConnectionId"], ref["fieldId"])),
              "sources": [{"id": source.pk, "generation": source.web_schema_generation,
                           "active": source.is_active, "channel": source.channel_id,
                           "fields": source.config.get("fields", [])}
                          for source in sources(binding)]}
    return hashlib.sha256(dumps(policy).encode()).hexdigest()
