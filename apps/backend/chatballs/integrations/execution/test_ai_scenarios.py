"""Scenario policies share the agent card value, including concurrent approval."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections

from chatballs.integrations.execution.ai_launch import launch_ai
from chatballs.integrations.execution.ai_policy import bind
from chatballs.integrations.execution.approvals import invocation_digest
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.scenario_agent_policies import save as save_policies
from chatballs.integrations.execution.test_ai_bridge import AgentExecutionCase
from chatballs.integrations.scenario_state.agent_grants import AgentActionGrant
from chatballs.tenancy.database import tenant_atomic


class AgentScenarioTests(AgentExecutionCase):
    def advance_until(self, run, expected):
        for _ in range(100):
            run_one(self.tenant, run.public_id, registry=self.registry)
            if self.state(run) == expected:
                return
        self.fail(f"Run did not reach {expected}: {self.state(run)}")

    def test_automatic_write_keeps_delegate_policy_after_agent_runtime_merge(self):
        from chatballs.integrations.execution.automation import launch_automatic
        from chatballs.integrations.scenario_state.automation import ScenarioAutomation

        trigger = {"id": "api", "kind": "api"}
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["triggers"] = [trigger]
            document["access"]["delegated"] = True
            self.scenario.definition = document
            self.scenario.save()
            ScenarioAutomation.objects.create(scenario=self.scenario, delegate=self.tenant.membership)
        run, _ = launch_automatic(self.tenant, self.scenario, trigger, key="automatic", registry=self.registry)
        self.advance_until(run, "completed")
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(self.calls), 1)
        with tenant_atomic(self.tenant):
            self.assertEqual(run.definition["triggerKind"], "api")
            self.assertNotIn("ai", run.definition)

    def test_composite_snapshot_keeps_agent_policy_and_link_context(self):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["triggers"] = [{"id": "agent", "kind": "ai", "agents": [self.agent.pk]}]
            document["steps"].append({**document["steps"][0], "id": "two"})
            self.scenario.definition = document
            self.scenario.save()
            save_policies(self.tenant, self.scenario, [{"agent": self.agent.pk, "mode": "ask", "revision": 0}])
            grant = AgentActionGrant.objects.get(agent=self.agent, scenario=self.scenario)
            binding = bind(grant, self.conversation)
        run = launch_ai(self.tenant, binding, {}, "composite", registry=self.registry)
        with tenant_atomic(self.tenant):
            self.assertEqual(run.definition["ai"]["grant"], grant.pk)
            self.assertEqual(run.definition["links"], [])
        self.advance_until(run, "approval")
        self.assertEqual(self.state(run), "approval")
        self.assertEqual(self.calls, [])
        with tenant_atomic(self.tenant):
            step = run.steps.get(state="approval")
            digest = invocation_digest(step, run)
        control(tenant=self.tenant, public_id=run.public_id, action="approve", digest=digest, path=step.path)
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(len(self.calls), 1)

    def test_policy_api_is_explicit_atomic_and_checks_revision(self):
        url = f"/api/v1/organizations/{self.organization.public_id}/integrations/agent-actions/{self.channel.pk}/"
        target = f"operation:{self.integration.pk}:{self.operation.key}"
        with patch("chatballs.integrations.execution.agent_actions.default_registry", return_value=self.registry):
            self.assertEqual(self.client.get(url).status_code, 200)
            denied = self.client_for(self.employee).put(url, {"items": [{"id": target, "mode": "ask", "revision": 1}]}, format="json")
            self.assertEqual(denied.status_code, 403)
            conflict = self.client.put(url, {"items": [{"id": target, "mode": "ask", "revision": 1},
                {"id": "missing", "mode": "self", "revision": 0}]}, format="json")
            self.assertEqual(conflict.status_code, 409)
            with tenant_atomic(self.tenant):
                self.grant.refresh_from_db()
                self.assertEqual((self.grant.mode, self.grant.revision), ("self", 1))
            saved = self.client.put(url, {"items": [{"id": target, "mode": "ask", "revision": 1}]}, format="json")
            self.assertEqual(saved.status_code, 200, saved.content)
            stale = self.client.put(url, {"items": [{"id": target, "mode": "self", "revision": 1}]}, format="json")
            self.assertEqual(stale.status_code, 409)

    def test_scenario_editor_grant_is_the_only_policy_used_by_runtime(self):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["triggers"] = [{"id": "agent", "kind": "ai", "agents": [self.agent.pk]}]
            # The old global setting must never override an explicit pair grant.
            document["access"]["aiMode"] = "off"
            self.scenario.definition = document
            self.scenario.save()
            save_policies(self.tenant, self.scenario, [{"agent": self.agent.pk, "mode": "self", "revision": 0}])
            grant = AgentActionGrant.objects.get(agent=self.agent, scenario=self.scenario)
            binding = bind(grant, self.conversation)
        run = launch_ai(self.tenant, binding, {}, "scenario", registry=self.registry)
        self.assertEqual(run.state, "queued")
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "completed")
        with tenant_atomic(self.tenant):
            save_policies(self.tenant, self.scenario, [{"agent": self.agent.pk, "mode": "off", "revision": 1}])
            grant.refresh_from_db()
            self.assertEqual(grant.mode, "off")
        with self.assertRaises(ExecutionDenied):
            launch_ai(self.tenant, binding, {}, "another", registry=self.registry)

    def test_concurrent_employee_confirmation_has_one_winner(self):
        run = self.ask()
        with tenant_atomic(self.tenant):
            digest = invocation_digest(run.steps.get(), run)
        barrier = Barrier(2)
        def approve():
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                try:
                    control(tenant=self.tenant, public_id=run.public_id, action="approve", digest=digest)
                    return "approved"
                except ExecutionDenied:
                    return "denied"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(approve) for _ in range(2)]
            self.assertEqual(sorted(future.result(timeout=40) for future in futures), ["approved", "denied"])
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(len(self.calls), 1)
