"""Issue a native, consent-gated session for an owned demo contact."""

from copy import copy
from secrets import token_urlsafe
from urllib.parse import urlencode

from django.core import signing

from chatballs.conversations.control_services import return_locked_to_ai
from chatballs.conversations.domain_events import operation_key, record_fact
from chatballs.conversations.models import (
    ConnectionIdentity,
    ControlMode,
    Conversation,
    LifecycleState,
)
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.local_access import local_demo_enabled
from chatballs.identity.demo_seed.north_wind.state import ShopError
from chatballs.identity.demo_seed.registry import runtime_recording
from chatballs.identity.operation_modes import autonomous_allowed
from chatballs.webchat.consent import has_current_consent, record_acceptance, validate_acceptance
from chatballs.webchat.models import WebChatWidget, WebSession
from chatballs.webchat.sessions import hash_session_token

_SALT = "north-wind-prepared-chat"


def activate_prepared_dialogue(session):
    """Hand the original prepared thread to its agent on the first customer message."""
    connection = session.connection
    if not local_demo_enabled() or not connection.config.get("demoGeneration"):
        return
    if not (connection.config.get("northWindStorefront") or connection.config.get("northWindSupport")
            or connection.config.get("northWindExecutorWidget")):
        return
    if session.widget_id is None or not has_current_consent(session):
        return
    dataset = DemoDataset.objects.filter(
        organization_id=session.organization_id, generation=connection.config["demoGeneration"],
        status__in=(DemoDatasetStatus.INSTALLED, DemoDatasetStatus.REINSTALLING),
    ).first()
    if dataset is None:
        return
    binding = next((
        item for route, item in dataset.shop_state.get("supportDialogs", {}).items()
        if route != "delivery" and item.get("widgetKey") == session.widget.public_key
        and item["connectionId"] == connection.pk and item["identityId"] == session.identity_id
    ), None)
    if binding is None:
        return
    conversation = Conversation.objects.select_for_update().filter(
        pk=binding["conversationId"], organization_id=session.organization_id, connection=connection,
        contact_id=session.identity.contact_id, lifecycle=LifecycleState.OPEN, control_mode=ControlMode.HUMAN,
    ).first()
    if conversation is None:
        return
    operation_id = operation_key("north-wind-prepared-start", conversation.pk)
    if conversation.domain_events.filter(operation_id=operation_id).exists():
        return
    if dataset.finished_at and conversation.domain_events.filter(
        actor_kind="HUMAN", occurred_at__gt=dataset.finished_at,
    ).exists():
        return
    candidate = copy(conversation)
    candidate.control_mode = ControlMode.AI
    candidate.assigned_operator_id = None
    if not autonomous_allowed(
        connection.channel, organization=connection.organization, connection=connection, conversation=candidate,
    ):
        return
    return_locked_to_ai(conversation)
    record_fact(conversation, "QUEUE_EXITED", operation_id=operation_id)


def prepared_chat_path(dataset, route):
    widget_key = dataset.shop_state["supportDialogs"][route]["widgetKey"]
    ticket = prepared_chat_ticket(dataset.organization_id, dataset.generation, route, widget_key)
    return "/chat/?" + urlencode({"widgetKey": widget_key, "demoDialog": route}) + "#" + urlencode({"entry": ticket})


def prepared_chat_ticket(organization_id, generation, route, widget_key):
    return signing.dumps([organization_id, str(generation), route, widget_key], salt=_SALT)


def accept_prepared_chat(context, widget, ticket, *, consent_version, pre_chat_fields):
    if not local_demo_enabled() or not isinstance(ticket, str) or not 0 < len(ticket) <= 1024:
        return None
    try:
        organization_id, generation, route, widget_key = signing.loads(ticket, salt=_SALT)
    except (signing.BadSignature, ValueError, TypeError):
        return None
    if (organization_id, widget_key) != (context.organization_id, widget.public_key):
        return None
    from chatballs.identity.demo_seed.north_wind.storefront_artifacts import storefront_artifacts

    with storefront_artifacts(widget.integration) as current:
        if not current:
            return None
        try:
            dataset = locked_dataset(context, generation)
            binding = dataset.shop_state.get("supportDialogs", {}).get(route, {})
            if binding.get("widgetKey") != widget_key:
                return None
            validate_acceptance(widget, consent_version, pre_chat_fields)
            return issue_prepared_session(dataset, binding, consent=(consent_version, pre_chat_fields))
        except ShopError:
            return None


def locked_dataset(tenant, generation):
    dataset = DemoDataset.objects.select_for_update().filter(
        organization_id=tenant.organization_id, generation=generation, status=DemoDatasetStatus.INSTALLED,
    ).first()
    if dataset is None:
        raise ShopError("demo_generation_unavailable")
    return dataset


def issue_prepared_session(dataset, binding, *, consent=None):
    widget = WebChatWidget.objects.filter(
        organization_id=dataset.organization_id, public_key=binding.get("widgetKey"),
        integration_id=binding.get("connectionId"), status="PUBLISHED",
    ).select_related("integration").first()
    identity = ConnectionIdentity.objects.filter(
        pk=binding.get("identityId"), connection_id=binding.get("connectionId"),
    ).first()
    if (widget is None or identity is None or not widget.integration.is_active
            or widget.integration.config.get("demoGeneration") != str(dataset.generation)):
        raise ShopError("demo_dialog_unavailable")
    token = token_urlsafe(32)
    with runtime_recording(dataset):
        session = WebSession.objects.create(
            organization_id=dataset.organization_id, token_hash=hash_session_token(token),
            connection=widget.integration, identity=identity, widget=widget,
        )
        if consent is not None:
            version, fields = consent
            record_acceptance(session, version=version, fields=fields)
    return {"widgetKey": widget.public_key, "token": token}
