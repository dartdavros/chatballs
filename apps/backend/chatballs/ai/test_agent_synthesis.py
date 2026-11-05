from chatballs.ai.test_agent_cards import AgentCardTestCase
from chatballs.identity.models import Organization
from chatballs.integrations.models import Integration
from chatballs.speech.checking import finish_check, prepare_check
from chatballs.testing import system_tenant_context


class AgentSynthesisSettingsTests(AgentCardTestCase):
    def speech_connection(self, organization=None):
        return Integration.objects.create(
            organization=organization or self.organization, name="Speech", kind="SPEECH_PROVIDER",
            provider="YANDEX_SPEECHKIT", secret="unit-test-never-sent", status="OK",
            config={"folder_id": "unit-folder"},
        )

    def test_tts_is_explicit_and_unrelated_patches_keep_its_selection(self):
        card = self.create_agent().json()["agent"]
        self.assertIsNone(card["synthesisIntegrationId"])
        self.assertEqual(card["synthesisVoice"], "")
        provider = self.speech_connection()
        url = f"/api/v1/agents/{card['id']}/"
        response = self.client.patch(url, {"synthesisIntegrationId": provider.id,
                                           "synthesisModel": "general", "synthesisVoice": "alena"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        card = response.json()["agent"]
        self.assertIsNone(card["providerIntegrationId"])
        self.assertIsNone(card["transcriptionIntegrationId"])
        self.assertEqual(card["synthesisIntegrationId"], provider.id)
        response = self.client.patch(url, {"instructions": "Updated"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["agent"]["synthesisVoice"], "alena")
        self.assertEqual(response.json()["agent"]["synthesisModel"], "general")
        response = self.client.patch(url, {"synthesisIntegrationId": None}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(response.json()["agent"]["synthesisIntegrationId"])

    def test_foreign_integration_and_unknown_voice_are_rejected(self):
        card = self.create_agent().json()["agent"]
        other = Organization.objects.create(name="Other", slug="other-tts-settings")
        foreign = self.speech_connection(other)
        url = f"/api/v1/agents/{card['id']}/"
        for body in ({"synthesisIntegrationId": foreign.id}, {"synthesisVoice": "unknown"},
                     {"synthesisModel": "unknown"}):
            response = self.client.patch(url, body, format="json")
            self.assertEqual(response.status_code, 400, response.content)

    def test_tts_check_failure_does_not_disable_working_stt(self):
        provider = self.speech_connection()
        job = prepare_check(provider, "tts")
        result = finish_check(system_tenant_context(self.organization), job, "access_denied")
        self.assertEqual(result.status, "OK")
        self.assertEqual(result.config["tts_check"]["status"], "ERROR")
        self.assertEqual(result.config["tts_check"]["error"], "access_denied")
