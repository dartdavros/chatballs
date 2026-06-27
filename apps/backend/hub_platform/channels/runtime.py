from hub_platform.ai.invocation import channel_chat
from hub_platform.ai.provider.base import ChatMessage, ChatResult


def run_channel_turn(*, channel, message: str, history: list[dict] | None = None) -> ChatResult:
    """One AI turn for a processing channel (M1.2a, ADR-HUB-0019).

    Uses the channel's live system prompt + model; knowledge retrieval and
    immutable channel releases arrive in M1.2b.
    """
    messages: list[ChatMessage] = []
    if channel.system_prompt.strip():
        messages.append(ChatMessage(role="system", content=channel.system_prompt))
    for item in history or []:
        messages.append(ChatMessage(role=str(item.get("role", "user")), content=str(item.get("content", ""))))
    messages.append(ChatMessage(role="user", content=message))
    return channel_chat(channel=channel, messages=messages, purpose="channel_test_chat")
