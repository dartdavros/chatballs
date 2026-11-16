from uuid import uuid4

from chatballs.ai.external_agents.config_models import ExternalAgentBinding
from chatballs.ai.external_agents.readiness import ready
from chatballs.ai.external_agents.testing import ConfigurationCase
from chatballs.ai.models import Skill
from chatballs.ai.template_runtime_testing import reply_template
from chatballs.integrations.models import Integration


class PolicyTests(ConfigurationCase):
    def test_explicit_source_field_pairs_and_templates_without_inherited_ai_access(self):
        identifier = self.connect()["connection"]["id"]
        field = str(uuid4())
        sources = [Integration.objects.create(organization=self.organization, name=name, kind="MESSENGER", provider="WEB",
                                              config={"fields": [{"id": field, "key": "city", "label": "City", "type": "string", "ai_access": "hidden"}]})
                   for name in ("First source", "Second source")]
        template = reply_template()
        Skill.objects.create(organization=self.organization, name="Template", description="Test", instruction="Test", templates=[template])
        refs = [{"sourceConnectionId": source.pk, "fieldId": field} for source in sources]
        self.bind(identifier, customFields=refs, templateIds=[template["id"]], proactiveEnabled=True,
                  ordinaryTimeout=120, longTimeout=7200, maximumTimeout=86400)
        binding = ExternalAgentBinding.objects.get()
        self.assertEqual(binding.custom_fields, refs)
        self.assertEqual(binding.standard_fields, [])
        self.assertEqual(binding.template_ids, [template["id"]])
        self.assertTrue(binding.proactive_enabled)
        from chatballs.ai.external_agents.config_bindings import select_execution
        select_execution(self.context, self.agent.pk, "external")
        self.organization.refresh_from_db()
        self.agent.refresh_from_db()
        self.assertTrue(ready(self.agent, self.organization))
        sources[0].config = {"fields": []}
        sources[0].save(update_fields=["config"])
        self.agent.refresh_from_db()
        self.assertFalse(ready(self.agent, self.organization))
