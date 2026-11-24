"""Record writes initiated through the registered, generation-bound demo widget."""

from contextlib import contextmanager

from django.db import transaction

from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.registry import runtime_recording
from chatballs.identity.operation_modes import lock_organization


@contextmanager
def storefront_artifacts(connection):
    if connection is None or not any(connection.config.get(key) for key in (
        "northWindStorefront", "northWindSupport", "northWindExecutorWidget",
    )):
        yield True
        return
    generation = connection.config.get("demoGeneration")
    if not generation:
        yield False
        return
    with transaction.atomic():
        lock_organization(connection.organization_id)
        dataset = DemoDataset.objects.select_for_update().filter(
            organization_id=connection.organization_id, generation=generation,
            status__in=(DemoDatasetStatus.INSTALLED, DemoDatasetStatus.REINSTALLING),
        ).first()
        if dataset is None or connection.pk not in {
            dataset.shop_state.get("storefront", {}).get("connectionId"),
            dataset.shop_state.get("pickupSite", {}).get("connectionId"),
            dataset.shop_state.get("loyaltySite", {}).get("connectionId"),
            dataset.shop_state.get("supportDialogs", {}).get("exchange", {}).get("connectionId"),
            dataset.shop_state.get("externalExecutor", {}).get("widgetConnectionId"),
        }:
            yield False
            return
        with runtime_recording(dataset):
            yield True
