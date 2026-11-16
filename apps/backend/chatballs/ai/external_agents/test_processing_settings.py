"""The settings form command controls new immutable request deadlines."""

from django.test import TestCase
from django.utils import timezone

from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.runtime_testing import RuntimeData


class ProcessingSettingsTests(RuntimeData, TestCase):
    def save_policy(self, **patch):
        saved = self.client.get(self.url).json()["connections"][0]
        binding = saved["bindings"][0]
        response = self.client.put(self.url + f"connections/{self.connection.pk}/configuration/", {
            "revision": saved["revision"], "bindingRevisions": {
                str(item["agentId"]): [item["revision"], item["policyVersion"]] for item in saved["bindings"]},
            "connection": {}, "removeAgentIds": [], "bindings": [{
                "agentId": binding["agentId"], "externalAgentId": binding["externalAgentId"],
                "policyAccepted": True, **patch}]}, format="json")
        return response

    def test_settings_roundtrip_ordinary_long_and_frozen_deadline_on_retry_progress_and_edit(self):
        ordinary = self.request()
        self.assertEqual((ordinary.deadline_at - ordinary.trigger.created_at).total_seconds(), 120)
        self.claim()
        self.accept(ordinary, self.result(ordinary))
        self.deliver()
        response = self.save_policy(processingMode="long", ordinaryTimeout=120, longTimeout=7200, maximumTimeout=86400)
        self.assertEqual(response.status_code, 200, response.content)
        saved = self.client.get(self.url).json()["connections"][0]["bindings"][0]
        self.assertEqual((saved["processingMode"], saved["longTimeout"], saved["maximumTimeout"]), ("long", 7200, 86400))
        row = self.request("long task")
        deadline = row.deadline_at
        self.assertEqual((deadline - row.trigger.created_at).total_seconds(), 7200)
        first = self.claim()
        self.settle(first)
        ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
        retry = self.claim()
        self.assertEqual(retry.request.body, first.request.body)
        self.settle(retry, {"version": "1", "requestId": str(row.public_id), "status": "accepted", "externalSessionId": "session-1"}, 202)
        for _ in range(2):
            ExternalAgentRequest.objects.filter(pk=row.pk).update(next_at=timezone.now())
            poll = self.claim()
            self.assertIsNotNone(poll)
            self.assertEqual(poll.request.method, "GET")
            self.settle(poll, {"version": "1", "requestId": str(row.public_id), "status": "processing", "externalSessionId": "session-1"})
            row.refresh_from_db()
            self.assertEqual(row.deadline_at, deadline)
        response = self.save_policy(processingMode="ordinary", longTimeout=3600, maximumTimeout=3600)
        self.assertEqual(response.status_code, 200, response.content)
        row.refresh_from_db()
        self.assertEqual(row.deadline_at, deadline)
        fresh = self.request("ordinary again")
        self.assertEqual((fresh.deadline_at - fresh.trigger.created_at).total_seconds(), 120)

    def test_maximum_is_enforced_by_same_settings_command(self):
        self.assertEqual(self.save_policy(processingMode="long", longTimeout=7200, maximumTimeout=3600).status_code, 400)
        self.assertEqual(self.save_policy(processingMode="long", longTimeout=3600, maximumTimeout=3600).status_code, 200)
        row = self.request()
        self.assertEqual((row.deadline_at - row.trigger.created_at).total_seconds(), 3600)
