from hub_platform.ai.invocation import channel_chat
from hub_platform.ai.models import ChannelAIRelease, ReleaseStatus
from hub_platform.ai.provider.base import ChatMessage, ChatResult
from hub_platform.ai.runtime import run_test_chat


def run_channel_turn(*, channel, message: str, history: list[dict] | None = None) -> ChatResult:
    """One AI turn for a processing channel (ADR-HUB-0019).

    Prefers the channel's published release (system prompts + knowledge retrieval,
    ADR-HUB-0007/0016). Falls back to the channel's live system prompt if no
    release is published yet.
    """
    release = (
        ChannelAIRelease.objects.filter(channel=channel, status=ReleaseStatus.PUBLISHED)
        .order_by("-version")
        .first()
    )
    if release is not None:
        return run_test_chat(release=release, message=message, history=history).result

    messages: list[ChatMessage] = []
    if channel.system_prompt.strip():
        messages.append(ChatMessage(role="system", content=channel.system_prompt))
    for item in history or []:
        messages.append(ChatMessage(role=str(item.get("role", "user")), content=str(item.get("content", ""))))
    messages.append(ChatMessage(role="user", content=message))
    return channel_chat(channel=channel, messages=messages, purpose="channel_chat")
