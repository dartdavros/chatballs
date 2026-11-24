"""Persist the mock carrier update and verified ingress in the same transaction."""

import json

from chatballs.identity.demo_models import DemoDataset
from chatballs.identity.demo_seed.north_wind.delivery import change_delivery
from chatballs.identity.demo_seed.north_wind.delivery_adapter import ADAPTER, EVENT, HEADER, ORDER_NUMBER, sign
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write
from chatballs.identity.demo_seed.registry import recording
from chatballs.integrations.automation_events.ingress import receive
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import ServiceConnectionSettings
from chatballs.integrations.service_connections.binding import ServiceUnavailable, load_credentials
from chatballs.tenancy.database import tenant_atomic


def update_shipment(tenant, generation, *, key, command):
    with tenant_atomic(tenant):
        dataset = DemoDataset.objects.select_for_update().filter(
            organization_id=tenant.organization_id, generation=generation,
        ).first()
        if dataset is None:
            raise ShopError("demo_generation_unavailable")
        event = execute_write(tenant, generation, change_delivery, key=key, command=command)
        if event["type"] != EVENT or event["orderNumber"] != ORDER_NUMBER or command["customer"] != "pavel":
            return event
        automation = dataset.shop_state.get("deliveryAutomation")
        if not automation:
            raise ShopError("delivery_automation_unavailable")
        connection = ServiceConnectionSettings.objects.filter(
            organization_id=tenant.organization_id, integration_id=automation["connectionId"],
            adapter_key=ADAPTER.key, integration__is_active=True,
        ).first()
        secret = load_credentials(connection).get("signature") if connection else None
        if not secret:
            raise ShopError("delivery_automation_unavailable")
        body = json.dumps(event, separators=(",", ":")).encode()
        # Same verified ingress as the service webhook endpoint, with no
        # loopback request across an uncommitted shop transaction.
        with recording(dataset) as recorder:
            before = recorder.sequence
            try:
                receipt, created = receive(tenant, connection.integration_id, EVENT, body, {HEADER: sign(secret, body)})
            except (ExecutionDenied, ServiceUnavailable) as error:
                raise ShopError("delivery_event_rejected") from error
            if created:
                for delivery in receipt.deliveries.filter(scenario_id__in=automation["scenarioIds"]):
                    recorder.record(delivery)
        if recorder.sequence != before:
            dataset.records_count = dataset.records.count()
            dataset.save(update_fields=["records_count"])
        return event
