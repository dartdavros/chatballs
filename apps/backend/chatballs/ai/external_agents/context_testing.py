"""Helpers for isolated context tests using native models and application services."""

from chatballs.ai.external_agents.config_models import ExternalAgentBinding
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.runtime_testing import RuntimeData
from chatballs.conversations.models import ContactFieldValue
from chatballs.integrations.models import Integration
from chatballs.integrations.services import IntegrationInput, update_integration
from chatballs.webchat.field_schema import fields_payload, normalize_fields


class ContextData(RuntimeData):
    def source(self, definitions, *, name="WEB", organization=None):
        return Integration.objects.create(
            organization=organization or self.organization, name=name, kind="MESSENGER", provider="WEB",
            config={"fields": normalize_fields(definitions, [])},
        )

    def grant(self, *sources, standard=()):
        return self.bind(self.connection.pk, standardFields=list(standard), customFields=[
            {"sourceConnectionId": source.pk, "fieldId": definition["id"]}
            for source in sources for definition in source.config["fields"]])

    def value(self, source, key, value, *, contact=None):
        return ContactFieldValue.objects.create(
            contact=contact or self.contact, integration=source, key=key, value=value)

    def change_schema(self, source, definitions):
        changed = update_integration(context=self.context, integration=source, data=IntegrationInput(
            provider="WEB", name=source.name, config={"fields": definitions},
        ))
        source.refresh_from_db()
        return changed

    def schema_payload(self, source):
        return fields_payload(source.config["fields"])

    def binding(self):
        return ExternalAgentBinding.objects.get(agent=self.agent)

    def frozen(self, row):
        row.refresh_from_db()
        return open_payload(row.snapshot_ciphertext)
