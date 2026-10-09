"""Deliver the completed turn outside its database transaction."""

from chatballs.conversations import transports


def deliver(turn, text: str) -> None:
    if not text or turn.conversation.connection is None:
        return
    transports.send_reply(
        turn.conversation.connection,
        chat_id=turn.conversation.external_chat_id,
        user_id=turn.user_id,
        text=text,
    )
