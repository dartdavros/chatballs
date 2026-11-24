"""Local customer photos and their native inbox messages."""

from hashlib import sha256

from chatballs.conversations.inbound_media import _store_attachment
from chatballs.conversations.ingest import ingest_inbound
from chatballs.conversations.models import (
    ConnectionIdentity,
    Conversation,
    Message,
    MessageAuthor,
    MessageKind,
)
from chatballs.conversations.transports.base import InboundFile, InboundMessage
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate
from chatballs.identity.demo_seed.north_wind.local_access import local_demo_enabled
from chatballs.identity.demo_seed.north_wind.state import ShopError
from chatballs.identity.demo_seed.registry import runtime_recording
from chatballs.tenancy.database import tenant_atomic

_PHOTO = "north-wind-zipper.jpg"


def _file():
    content = manifest.media_bytes(_PHOTO)
    return InboundFile(name=_PHOTO, content_type="image/jpeg", size=len(content), content=content, is_image=True)


def prepare_support_dialog(dataset, key, conversation):
    if conversation.connection.config.get("demoGeneration") != str(dataset.generation):
        raise RuntimeError("The North Wind support channel is not part of this demo generation")
    identity = ConnectionIdentity.objects.create(
        contact=conversation.contact, connection=conversation.connection,
        external_user_id=conversation.external_chat_id, display_name=conversation.contact.name,
    )
    dataset.shop_state.setdefault("supportDialogs", {})[key] = {
        "conversationId": conversation.pk, "identityId": identity.pk, "connectionId": conversation.connection_id,
    }


def seed_team_photo(conversation, at):
    message = Message.objects.create(conversation=conversation, author_type=MessageAuthor.CONTACT, kind=MessageKind.FILE)
    _store_attachment(conversation.connection, _file(), message)
    if not message.attachment:
        raise RuntimeError("The North Wind photo could not be stored")
    backdate(message, at)
    backdate(conversation, at, "last_message_at", "last_activity_at")


def receive_demo_photo(tenant, generation, *, key, dialog):
    if not local_demo_enabled():
        raise ShopError("demo_generation_unavailable")
    if not key or len(key) > 128:
        raise ShopError("idempotency_key_required")
    with tenant_atomic(tenant):
        dataset = DemoDataset.objects.select_for_update().filter(
            organization_id=tenant.organization_id, generation=generation,
            status=DemoDatasetStatus.INSTALLED,
        ).first()
        if dataset is None:
            raise ShopError("demo_generation_unavailable")
        binding = dataset.shop_state.get("supportDialogs", {}).get(dialog)
        if not binding:
            raise ShopError("demo_dialog_unavailable")
        conversation = Conversation.objects.select_related("connection", "contact").filter(
            organization_id=tenant.organization_id, pk=binding["conversationId"], connection_id=binding["connectionId"],
        ).first()
        if (conversation is None or conversation.connection.config.get("demoGeneration") != str(generation)
                or not conversation.connection.is_active):
            raise ShopError("demo_dialog_unavailable")
        external_id = "north-wind-photo:" + sha256(key.encode()).hexdigest()
        prior = conversation.messages.filter(external_id=external_id, kind=MessageKind.FILE).first()
        if prior is not None:
            return {"conversationId": conversation.pk, "messageId": prior.pk}
        identity = ConnectionIdentity.objects.filter(
            pk=binding["identityId"], contact=conversation.contact, connection=conversation.connection,
        ).first()
        if identity is None or conversation.lifecycle != "OPEN":
            raise ShopError("demo_dialog_unavailable")
        with runtime_recording(dataset):
            ingest_inbound(conversation.connection, InboundMessage(
                external_id=external_id, user_id=identity.external_user_id, chat_id=conversation.external_chat_id,
                display_name=identity.display_name, text="", files=(_file(),),
            ))
            message = conversation.messages.filter(external_id=external_id, kind=MessageKind.FILE).first()
            if message is None or not message.attachment:
                raise ShopError("demo_photo_unavailable")
        return {"conversationId": conversation.pk, "messageId": message.pk}
