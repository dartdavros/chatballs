from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from chatballs.i18n import t
from chatballs.integrations.adapters.bitrix24 import ADAPTER
from chatballs.integrations.execution.views import RunAPIView
from chatballs.integrations.scenarios.definition import Issue
from chatballs.integrations.scenarios.payloads import issue_payload
from chatballs.integrations.service_connections.binding import ServiceUnavailable
from chatballs.integrations.service_connections.payloads import adapter_payload


class ServiceFormContractTests(SimpleTestCase):
    def test_bitrix_exchange_contract_only_offers_supported_read_direction(self):
        entities = adapter_payload(ADAPTER)["entities"]
        self.assertTrue(entities)
        for entity in entities:
            self.assertEqual(entity["synchronization"], {"directions": ["reverse"], "deletion": ["unlink", "keep"]})

    def test_manual_lookup_explains_permission_failure_instead_of_not_found(self):
        view = RunAPIView()
        view.request = view.initialize_request(APIRequestFactory().get("/"))
        response = view.handle_exception(ServiceUnavailable("user_access_missing", adapter="bitrix24"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "user_access_missing")
        self.assertIn(t("services.bitrix24.error_users_text"), response.data["detail"])

    def test_null_validation_points_to_the_missing_value(self):
        issue = issue_payload(Issue("steps.0.inputs.fields.ASSIGNED_BY_ID.$", "null"))
        self.assertEqual(issue["message"], t("scenarios.required"))
