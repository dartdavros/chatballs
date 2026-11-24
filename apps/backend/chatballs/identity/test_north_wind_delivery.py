from unittest.mock import patch
from uuid import uuid4

from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.manifest import load
from chatballs.identity.demo_seed.north_wind.delivery_events import update_shipment
from chatballs.identity.demo_seed.north_wind.delivery_scenarios import load_delivery_scenarios
from chatballs.identity.demo_seed.north_wind.state import initial_state
from chatballs.identity.demo_seed.refs import DemoRefs
from chatballs.identity.demo_seed.registry import recording
from chatballs.integrations.automation_events.fanout import deliver_one
from chatballs.integrations.automation_events.scheduler import tick
from chatballs.integrations.execution.launch import launch
from chatballs.integrations.scenario_state.automation import EventDelivery, ScheduleCheckpoint
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.tenancy.database import tenant_atomic


class NorthWindDeliveryTests(DomainEventTestBase):
    @patch.dict("os.environ", {"CHATBALLS_LOCAL_NORTH_WIND": "1"})
    @patch("chatballs.identity.demo_seed.north_wind.delivery_scenarios.verify_delivery_service")
    def test_delivery_uses_native_event_schedule_and_confirmed_manual_run(self, verify_service):
        tenant = self.context
        with tenant_atomic(tenant):
            dataset = DemoDataset.objects.create(
                organization=self.organization, status=DemoDatasetStatus.INSTALLED,
                generation=uuid4(), shop_state=initial_state(),
            )
            with recording(dataset) as recorder:
                refs = DemoRefs(recorder=recorder, memberships={"elena": self.member, "igor": self.member})
                load_delivery_scenarios(refs, self.conversation, load("north_wind", "ru")["deliveryAutomation"])
            verify_service.assert_called_once()
            command = {"customer": "pavel", "order_number": 2043, "status": "delayed", "confirmed": True}
            event = update_shipment(tenant, dataset.generation, key="delay", command=command)
            self.assertEqual(update_shipment(tenant, dataset.generation, key="delay", command=command), event)
            receipt = EventReceipt.objects.get(event_key="delivery.delayed")
            delivery = EventDelivery.objects.get(receipt=receipt)
        deliver_one(tenant, delivery.pk)
        deliver_one(tenant, delivery.pk)
        with tenant_atomic(tenant):
            delivery.refresh_from_db()
            self.assertEqual(delivery.state, "delivered", delivery.error_code)
            self.assertEqual(delivery.run.conversation_id, self.conversation.pk)
            self.assertEqual(delivery.run.definition["triggerKind"], "service")
            checkpoint = ScheduleCheckpoint.objects.get()
        tick(tenant, now=checkpoint.due_at)
        with tenant_atomic(tenant):
            self.assertEqual(ScenarioRun.objects.count(), 2)
            scheduled = ScenarioRun.objects.get(scenario=checkpoint.scenario)
            self.assertEqual(scheduled.definition["triggerKind"], "schedule")
            definition = ScenarioDefinition.objects.get(pk=dataset.shop_state["deliveryAutomation"]["scenarioIds"][2])
        manual, _ = launch(
            tenant=tenant, scenario_id=definition.public_id, conversation_id=self.conversation.pk,
            trigger_key="check", parameters={},
        )
        with tenant_atomic(tenant):
            step = manual.steps.get()
            self.assertEqual(step.state, "approval")
