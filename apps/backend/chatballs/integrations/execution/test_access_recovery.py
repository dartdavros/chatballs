"""Revocation, cancellation after send, and an independently audited repeat."""

from dataclasses import replace
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from chatballs.identity.models import OrganizationMembership
from chatballs.integrations.adapters.contracts import (
    OperationHandlers,
    OperationResult,
    ResultState,
    RetryStrategy,
)
from chatballs.integrations.execution import checkpoints
from chatballs.integrations.execution.control import control
from chatballs.integrations.execution.repeat import intentional_repeat
from chatballs.integrations.execution.runner import _commit, _send_marker, run_one
from chatballs.integrations.execution.test_execution import ExecutionCase
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.steps import ScenarioStep
from chatballs.tenancy.database import tenant_atomic


class RecoveryAccessTests(ExecutionCase):
    def test_paused_connection_disabled_scenario_and_expired_approval_prevent_send(self):
        for reason in ("connection", "scenario", "approval"):
            with self.subTest(reason=reason):
                run = self.launch(key=reason)
                with tenant_atomic(self.tenant):
                    if reason == "connection":
                        self.integration.is_active = False
                        self.integration.save(update_fields=["is_active"])
                    elif reason == "scenario":
                        self.scenario.enabled = False
                        self.scenario.save(update_fields=["enabled"])
                    else:
                        run.steps.update(approval_expires_at=timezone.now() - timedelta(seconds=1))
                run_one(self.tenant, run.public_id, registry=self.registry)
                self.assertEqual(self.state(run), "failed")
                self.assertEqual(self.calls, [])
                with tenant_atomic(self.tenant):
                    self.integration.is_active = True
                    self.integration.save(update_fields=["is_active"])
                    self.scenario.enabled = True
                    self.scenario.save(update_fields=["enabled"])

    def test_revoked_actor_cannot_start_a_new_effect(self):
        run = self.launch()
        with tenant_atomic(self.tenant):
            OrganizationMembership.objects.filter(pk=self.tenant.membership_id).update(blocked_at=timezone.now())
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "failed")
        self.assertEqual(self.calls, [])

    def test_cancel_after_send_keeps_confirmed_result_and_never_rolls_it_back(self):
        run = self.launch()
        token = checkpoints.claim(self.tenant, run.public_id)
        self.assertTrue(_send_marker(self.tenant, token, "execute", self.registry))
        control(tenant=self.tenant, public_id=run.public_id, action="cancel")
        self.assertTrue(_commit(self.tenant, token, OperationResult(ResultState.COMPLETED, data={})))
        self.assertEqual(self.state(run), "completed")
        with tenant_atomic(self.tenant):
            run.refresh_from_db()
            self.assertIsNotNone(run.cancel_requested_at)

    def test_reconcile_after_revocation_reads_outcome_without_new_write(self):
        reads = []
        def reconcile(context, _operation, _continuation):
            reads.append(context.effect_key)
            return OperationResult(ResultState.COMPLETED, data={})
        self.operation = replace(self.operation, retry=RetryStrategy.RECONCILE,
            handlers=OperationHandlers(execute=self.effect, reconcile=reconcile))
        self.registry = self.make_registry()
        run = self.launch()
        token = checkpoints.claim(self.tenant, run.public_id)
        self.assertTrue(_send_marker(self.tenant, token, "execute", self.registry))
        self.expire(run)
        with tenant_atomic(self.tenant):
            OrganizationMembership.objects.filter(pk=self.tenant.membership_id).update(blocked_at=timezone.now())
        run_one(self.tenant, run.public_id, registry=self.registry)
        self.assertEqual(self.state(run), "completed")
        self.assertEqual(len(reads), 1)
        self.assertEqual(self.calls, [])

    def test_intentional_repeat_is_a_new_run_and_keeps_original_outcome(self):
        run = self.launch()
        with tenant_atomic(self.tenant):
            ScenarioRun.objects.filter(pk=run.pk).update(state="unknown", finished_at=timezone.now())
            run.steps.update(state="unknown")
        # The repeat helper resolves the installed contract. This boundary test
        # supplies the same in-memory descriptor to avoid any external request.
        from unittest.mock import patch
        with patch("chatballs.integrations.execution.actions.default_registry", return_value=self.registry):
            repeated = intentional_repeat(self.tenant, run.public_id, trigger_key="new-click", acknowledged=str(run.public_id))
        self.assertNotEqual(run.public_id, repeated.public_id)
        self.assertEqual(self.state(run), "unknown")
        self.assertEqual(self.state(repeated), "approval")

    def test_database_protects_effect_and_trigger_identity(self):
        run = self.launch()
        with tenant_atomic(self.tenant):
            with self.assertRaises(IntegrityError), transaction.atomic():
                ScenarioRun.objects.filter(pk=run.pk).update(trigger_key="different")
            with self.assertRaises(IntegrityError), transaction.atomic():
                ScenarioStep.objects.filter(run=run).update(path="different")
