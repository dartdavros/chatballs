"""Runtime API isolation and exact manual confirmations on PostgreSQL."""

from unittest.mock import patch

from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class RunAPITests(ExecutionCase):
    def test_paused_connection_is_shown_unavailable_without_sending(self):
        with tenant_atomic(self.tenant):
            self.integration.is_active = False
            self.integration.save(update_fields=["is_active"])
        url = f"/api/v1/organizations/{self.organization.public_id}/integrations/run-actions/"
        with patch("chatballs.integrations.execution.manual_catalog_queries.default_registry", return_value=self.registry), patch(
                "chatballs.integrations.execution.actions.default_registry", return_value=self.registry):
            response = self.as_runtime(lambda: self.client.get(url))
        self.assertEqual(response.status_code, 200, response.content)
        catalog = response.json()["items"]
        items = [item for item in catalog if item.get("connectionId") != "chatballs"]
        self.assertEqual({item["kind"] for item in items}, {"scenario", "operation"})
        self.assertTrue(all(item["available"] is False and item["reason"] for item in items))
        native = [item for item in catalog if item.get("connectionId") == "chatballs"]
        self.assertTrue(native)
        self.assertTrue(all(item["available"] for item in native))
        self.assertEqual(self.calls, [])

    def run_url(self, suffix="", organization=None):
        org = organization or self.organization
        return f"/api/v1/organizations/{org.public_id}/integrations/runs/{suffix}"

    def test_runtime_journal_and_details_do_not_disclose_other_tenants(self):
        run = self.launch(approve=False)
        client = self.client_for(self.other_owner)
        response = self.as_runtime(lambda: client.get(self.run_url(organization=self.other)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        response = self.as_runtime(lambda: client.get(self.run_url(f"{run.public_id}/", self.other)))
        self.assertEqual(response.status_code, 404)

    def test_employee_cannot_read_organization_journal_or_control_unrelated_run(self):
        run = self.launch(approve=False)
        client = self.client_for(self.employee)
        for suffix in ("", f"{run.public_id}/"):
            response = self.as_runtime(lambda suffix=suffix: client.get(self.run_url(suffix)))
            self.assertEqual(response.status_code, 409, response.content)
        for action in ("cancel", "reconcile", "approve"):
            response = self.as_runtime(lambda action=action: client.post(self.run_url(f"{run.public_id}/{action}/"), {}, format="json"))
            self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(self.state(run), "approval")

    def test_preview_has_no_run_and_changed_confirmation_cannot_send(self):
        url = f"/api/v1/organizations/{self.organization.public_id}/integrations/run-actions/"
        body = {"scenarioId": str(self.scenario.public_id), "triggerKey": "manual-api", "parameters": {}, "preview": True}
        with patch("chatballs.integrations.execution.actions.default_registry", return_value=self.registry):
            response = self.as_runtime(lambda: self.client.post(url, body, format="json"))
            self.assertEqual(response.status_code, 200, response.content)
            token = response.json()["preview"]["confirmation"]
            with tenant_atomic(self.tenant):
                self.assertEqual(ScenarioRun.objects.count(), 0)
                self.scenario.revision += 1
                self.scenario.save(update_fields=["revision"])
            response = self.as_runtime(lambda: self.client.post(url, {**body, "preview": False, "confirmation": token}, format="json"))
            self.assertEqual(response.status_code, 409, response.content)
        with tenant_atomic(self.tenant):
            self.assertEqual(ScenarioRun.objects.count(), 0)
        self.assertEqual(self.calls, [])

    def test_catalog_rejects_unknown_conversation_before_exposing_file_names(self):
        url = f"/api/v1/organizations/{self.organization.public_id}/integrations/run-actions/?conversation=999999999"
        response = self.as_runtime(lambda: self.client_for(self.employee).get(url))
        self.assertEqual(response.status_code, 404, response.content)

    def test_detail_lists_only_controls_authorized_in_current_state(self):
        run = self.launch(approve=False)
        response = self.as_runtime(lambda: self.client.get(self.run_url(f"{run.public_id}/")))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(set(response.json()["run"]["controls"]), {"approve", "cancel"})
        response = self.as_runtime(lambda: self.client.post(self.run_url(f"{run.public_id}/cancel/"), {}, format="json"))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["run"]["controls"], ["repeat"])
