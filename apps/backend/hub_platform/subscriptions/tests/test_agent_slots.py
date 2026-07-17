from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections, connections
from django.test import TestCase, TransactionTestCase

from hub_platform.ai.models import AIAgent, AIAgentStatus
from hub_platform.channels.models import Channel
from hub_platform.identity.models import Organization
from hub_platform.subscriptions.agent_slots import set_agent_status
from hub_platform.subscriptions.errors import InvalidAgentTransition, QuotaExceeded
from hub_platform.subscriptions.keys import QuotaKey
from hub_platform.subscriptions.models import (
    Subscription,
    SubscriptionStatus,
    UsageCounter,
    UsageLedgerEntry,
)
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.testing import system_tenant_context


def _draft_agent(organization: Organization, code: str) -> AIAgent:
    channel = Channel.objects.create(
        organization=organization,
        code=code,
        name=code,
    )
    return AIAgent.objects.create(
        organization=organization,
        channel=channel,
        name=code,
        status=AIAgentStatus.DRAFT,
    )


class AgentSlotLifecycleTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Agents", slug="agents")
        self.context = system_tenant_context(self.organization)
        self.first = _draft_agent(self.organization, "first")
        self.second = _draft_agent(self.organization, "second")
        create_test_subscription(self.organization, quantity=1)

    def test_only_active_agent_occupies_slot_and_transition_is_idempotent(self) -> None:
        active = set_agent_status(
            context=self.context,
            agent_id=self.first.id,
            target_status=AIAgentStatus.ACTIVE,
        )
        replay = set_agent_status(
            context=self.context,
            agent_id=self.first.id,
            target_status=AIAgentStatus.ACTIVE,
        )
        self.assertEqual(active.id, replay.id)
        self.assertEqual(UsageCounter.objects.get().used_value, 1)
        self.assertEqual(UsageLedgerEntry.objects.count(), 1)
        with self.assertRaises(QuotaExceeded):
            set_agent_status(
                context=self.context,
                agent_id=self.second.id,
                target_status=AIAgentStatus.ACTIVE,
            )

        set_agent_status(
            context=self.context,
            agent_id=self.first.id,
            target_status=AIAgentStatus.DISABLED,
        )
        set_agent_status(
            context=self.context,
            agent_id=self.second.id,
            target_status=AIAgentStatus.ACTIVE,
        )
        self.assertEqual(UsageCounter.objects.get().used_value, 1)
        self.assertEqual(
            list(
                AIAgent.objects.filter(status=AIAgentStatus.ACTIVE).values_list(
                    "id", flat=True
                )
            ),
            [self.second.id],
        )

    def test_archived_agent_is_terminal(self) -> None:
        set_agent_status(
            context=self.context,
            agent_id=self.first.id,
            target_status=AIAgentStatus.ARCHIVED,
        )
        with self.assertRaises(InvalidAgentTransition):
            set_agent_status(
                context=self.context,
                agent_id=self.first.id,
                target_status=AIAgentStatus.ACTIVE,
            )

    def test_suspension_does_not_prevent_releasing_active_slot(self) -> None:
        set_agent_status(
            context=self.context,
            agent_id=self.first.id,
            target_status=AIAgentStatus.ACTIVE,
        )
        Subscription.objects.filter(organization=self.organization).update(
            status=SubscriptionStatus.SUSPENDED
        )
        set_agent_status(
            context=self.context,
            agent_id=self.first.id,
            target_status=AIAgentStatus.DISABLED,
        )
        self.assertEqual(UsageCounter.objects.get().used_value, 0)


class ConcurrentAgentSlotTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Concurrent", slug="concurrent")
        self.agent_ids = [
            _draft_agent(self.organization, "concurrent-first").id,
            _draft_agent(self.organization, "concurrent-second").id,
        ]
        create_test_subscription(self.organization, quantity=1)

    def test_parallel_activation_cannot_oversubscribe(self) -> None:
        barrier = Barrier(2)

        def activate(agent_id: int) -> str:
            close_old_connections()
            organization = Organization.objects.get(pk=self.organization.pk)
            context = system_tenant_context(organization)
            barrier.wait()
            try:
                set_agent_status(
                    context=context,
                    agent_id=agent_id,
                    target_status=AIAgentStatus.ACTIVE,
                )
                return "active"
            except QuotaExceeded:
                return "limited"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(activate, self.agent_ids))
        self.assertCountEqual(outcomes, ["active", "limited"])
        self.assertEqual(
            AIAgent.objects.filter(status=AIAgentStatus.ACTIVE).count(),
            1,
        )
        self.assertEqual(
            UsageCounter.objects.get(quota_definition__key=QuotaKey.AI_AGENT_SLOTS).used_value,
            1,
        )
