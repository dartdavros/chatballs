"""PostgreSQL composition test helpers; no installed adapter or demo data."""

from django.test import override_settings

from chatballs.integrations.adapters.registry import build_registry, reset_registry
from chatballs.integrations.execution import contract_testing
from chatballs.integrations.execution.launch import launch
from chatballs.integrations.execution.runner import run_one
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.tenancy.database import tenant_atomic


class CompositionCase(ExecutionCase):
    def setUp(self):
        super().setUp()
        modules = ("chatballs.integrations.execution.contract_testing", "chatballs.integrations.execution.ledger_contract_testing")
        self.enterContext(override_settings(CHATBALLS_SERVICE_ADAPTERS=modules))
        reset_registry()
        self.addCleanup(reset_registry)
        contract_testing.CALLS.clear()
        self.registry = build_registry(modules)
        with tenant_atomic(self.tenant):
            ServiceConnectionSettings.objects.filter(integration=self.integration).update(
                adapter_key="independent", adapter_version=1, auth_method="token", credentials='{"signature":"test-signature"}')
            self.other_connection = Integration.objects.create(organization=self.organization, name="Second independent service",
                kind="SERVICE", provider="ADAPTER", is_active=True, status="OK")
            ServiceConnectionSettings.objects.create(organization=self.organization, integration=self.other_connection,
                adapter_key="independent", adapter_version=1, auth_method="token", credentials='{"signature":"other-signature"}')

    def action(self, sid, value="hello", connection=None, operation="project"):
        return {"id": sid, "kind": "action", "connection": str((connection or self.integration).pk),
                "target": f"service:{operation}", "inputs": {"value": value if isinstance(value, dict) else {"source": "constant", "value": value}}}

    def start(self, steps, *, key="composite", outputs=None, conversation_id=None):
        with tenant_atomic(self.tenant):
            document = self.scenario.definition
            document["steps"] = steps
            if outputs:
                document["outputs"] = outputs
                document["results"] = {"type": "object", "properties": {"value": {"type": "string", "required": True}}}
            self.scenario.definition = document
            self.scenario.save()
        return launch(tenant=self.tenant, scenario_id=self.scenario.public_id,
                      trigger_key=key, parameters={}, registry=self.registry, conversation_id=conversation_id)[0]

    def pump(self, run, *, limit=100):
        for _ in range(limit):
            run_one(self.tenant, run.public_id, registry=self.registry)
            with tenant_atomic(self.tenant):
                run.refresh_from_db()
                if run.finished_at or run.state in {"unknown", "approval"}:
                    return run
        return run
