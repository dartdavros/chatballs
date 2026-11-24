"""Collect the owned effects of the native site-event workflow before reset."""

from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.domain_events import operation_key
from chatballs.conversations.models import Conversation, Message
from chatballs.events.models import OutboxEvent
from chatballs.identity.demo_seed.north_wind.delivery_artifacts import register_run
from chatballs.integrations.scenario_state.automation import EventDelivery
from chatballs.integrations.scenario_state.receipts import EventReceipt
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.notifications.models import Notification
from chatballs.webchat.proactive_models import SiteEventLaunch


def register_site_artifacts(dataset):
    for key in ("pickupSite", "loyaltySite"):
        site = dataset.shop_state.get(key)
        if site:
            _register_site(dataset, site)


def _register_site(dataset, site):
    from chatballs.identity.demo_seed.registry import recording

    launches = SiteEventLaunch.objects.filter(
        organization_id=dataset.organization_id, session__connection_id=site["connectionId"], rule_id=site["ruleId"],
    )
    receipts = EventReceipt.objects.filter(organization_id=dataset.organization_id, pk__in=launches.values("receipt_id"))
    deliveries = EventDelivery.objects.filter(receipt__in=receipts, scenario_id=site["scenarioId"])
    runs = ScenarioRun.objects.filter(
        pk__in=deliveries.values("run_id"), scenario_id=site["scenarioId"], revision=site["scenarioRevision"],
    )
    with recording(dataset) as recorder:
        for rows in (receipts, OutboxEvent.objects.filter(
            organization_id=dataset.organization_id, event_type="integrations.fanout",
            payload__receiptId__in=list(receipts.values_list("pk", flat=True)),
        ), launches, deliveries):
            for row in rows.iterator(chunk_size=100):
                recorder.record_existing(row)
        for run in runs.select_for_update().iterator(chunk_size=100):
            register_run(recorder, run)
        for launch in launches.exclude(conversation_id=None).iterator(chunk_size=100):
            _register_conversation(recorder, launch, site["connectionId"])


def _register_conversation(recorder, launch, connection_id):
    conversation = Conversation.objects.filter(pk=launch.conversation_id, connection_id=connection_id,
                                                transport_meta__siteEventLaunchId=launch.pk).first()
    if conversation is None:
        return
    recorder.record_existing(conversation)
    if launch.response_id is None:
        return
    replies = Message.objects.filter(conversation=conversation, author_type="AI", ai_delivery__siteEventLaunchId=launch.pk)
    for reply in replies:
        recorder.record_existing(reply)
        for event in ConversationEvent.objects.filter(conversation=conversation, actor_kind="AI", event_type="PUBLIC_REPLY",
                                                     operation_id=operation_key("reply", reply.pk)):
            recorder.record_existing(event)
    for note in Notification.objects.filter(organization_id=conversation.organization_id,
                                            dedup_key=f"handoff:{conversation.pk}"):
        recorder.record_existing(note)
