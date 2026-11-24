import uuid

from chatballs.conversations.ingest import ingest_inbound
from chatballs.conversations.models import (
    Conversation,
    LifecycleState,
)
from chatballs.conversations.transports.base import InboundMessage
from chatballs.webchat.configuration import public_config as public_config
from chatballs.webchat.message_history import messages_payload as messages_payload
from chatballs.webchat.models import WebSession
from chatballs.webchat.sessions import (
    hash_session_token as hash_session_token,
)
from chatballs.webchat.sessions import (
    issue_session as issue_session,
)
from chatballs.webchat.sessions import (
    origin_allowed as origin_allowed,
)
from chatballs.webchat.sessions import (
    resolve_session as resolve_session,
)
from chatballs.webchat.sessions import (
    web_connection_for_channel as web_connection_for_channel,
)


def post_message(session: WebSession, text: str) -> None:
    inbound = InboundMessage(
        external_id=uuid.uuid4().hex,
        user_id=session.identity.external_user_id,
        chat_id="",
        text=text,
        display_name=session.identity.display_name,
    )
    _ingest_from_widget(session, inbound)


def post_voice(session: WebSession, *, content: bytes, content_type: str, duration: int) -> None:
    """Голосовое из виджета: байты приходят телом запроса, скачивать нечего."""
    inbound = InboundMessage(
        external_id=uuid.uuid4().hex,
        user_id=session.identity.external_user_id,
        chat_id="",
        text="",
        display_name=session.identity.display_name,
        voice_content=content,
        voice_mime=content_type,
        voice_duration=duration,
    )
    _ingest_from_widget(session, inbound)


def post_file(session: WebSession, *, content: bytes, filename: str, content_type: str, caption: str = "") -> None:
    """Файл из виджета: байты приходят телом запроса, подпись — текстом."""
    from chatballs.conversations.transports.base import (
        InboundFile,
        guess_content_type,
        safe_filename,
    )

    name = safe_filename(filename)
    mime = content_type or guess_content_type(name)
    inbound = InboundMessage(
        external_id=uuid.uuid4().hex,
        user_id=session.identity.external_user_id,
        chat_id="",
        text=caption,
        display_name=session.identity.display_name,
        files=(InboundFile(name=name, content_type=mime, size=len(content), content=content, is_image=mime.startswith("image/")),),
    )
    _ingest_from_widget(session, inbound)


def _ingest_from_widget(session, inbound, *, remember_widget=True):
    from rest_framework.exceptions import PermissionDenied

    from chatballs.identity.demo_seed.north_wind.storefront_artifacts import storefront_artifacts

    with storefront_artifacts(session.connection) as current:
        if not current:
            raise PermissionDenied()
        if inbound.text or inbound.voice_content:
            from chatballs.identity.demo_seed.north_wind.prepared_widget import (
                activate_prepared_dialogue,
            )

            activate_prepared_dialogue(session)
        ingest_inbound(session.connection, inbound)
        if remember_widget:
            _remember_widget(session)


def _remember_widget(session: WebSession) -> None:
    conversation = (
        Conversation.objects.filter(
            channel=session.connection.channel,
            contact=session.identity.contact,
            lifecycle=LifecycleState.OPEN,
        )
        .order_by("-last_activity_at")
        .first()
    )
    if conversation is not None:
        metadata = conversation.transport_meta or {}
        if "webChatWidgetId" not in metadata:
            conversation.transport_meta = {
                **metadata,
                "webChatWidgetId": session.widget_id,
            }
            conversation.save(update_fields=["transport_meta"])


def normalize_phone(raw: str) -> str:
    """Нормализация телефона из формы виджета: только + и цифры, 10–15 цифр."""
    phone = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
    if phone.count("+") > 1 or (phone and "+" in phone[1:]):
        return ""
    digits = phone.lstrip("+")
    if not (10 <= len(digits) <= 15):
        return ""
    return phone


def post_contact(session: WebSession, phone: str) -> None:
    # Ответ клиента на запрос контакта: сообщение без текста, с телефоном —
    # ingest сохранит его в Contact.phone и подтвердит без AI-хода.
    inbound = InboundMessage(
        external_id=uuid.uuid4().hex,
        user_id=session.identity.external_user_id,
        chat_id="",
        text="",
        display_name=session.identity.display_name,
        phone=phone,
    )
    _ingest_from_widget(session, inbound, remember_widget=False)
