"""TTS reads the same customer audience as widget history, never browser text."""

from chatballs.speech.errors import SpeechError
from chatballs.webchat.message_selectors import session_messages


def synthesis_message(session, message_id):
    message = session_messages(session).filter(
        pk=message_id, author_type="AI", kind="", system_event="", ai_turn_state__in=["NONE", "DONE"],
    ).first()
    if message is None or not message.text.strip():
        raise SpeechError("tts_unavailable")
    # Persisted delivery acknowledgement is the final-public-answer boundary.
    if (message.ai_reply_to_id or message.ai_delivery) and not message.ai_delivery.get("sent"):
        raise SpeechError("tts_unavailable")
    return message
