from dataclasses import dataclass

from hub_platform.ai.invocation import invoke_chat
from hub_platform.ai.models import KnowledgeFragment, ProductAIRelease, PromptCategory
from hub_platform.ai.provider.base import ChatMessage, ChatResult
from hub_platform.ai.retrieval import KnowledgeRetriever

_PROMPT_ORDER = [
    PromptCategory.SYSTEM,
    PromptCategory.QUALIFICATION,
    PromptCategory.SALES_BEHAVIOR,
    PromptCategory.OPERATOR_HANDOFF,
]


@dataclass(frozen=True)
class TestChatResult:
    result: ChatResult
    fragments: list[KnowledgeFragment]
    handoff_suggested: bool


def _release_system_prompt(release: ProductAIRelease) -> str:
    by_category = {
        link.prompt_version.document.category: link.prompt_version
        for link in release.prompt_versions.select_related("prompt_version__document")
    }
    parts = [
        by_category[category].content
        for category in _PROMPT_ORDER
        if category in by_category and by_category[category].content.strip()
    ]
    return "\n\n".join(parts)


def run_test_chat(*, release: ProductAIRelease, message: str, history: list[dict] | None = None) -> TestChatResult:
    fragments = KnowledgeRetriever().retrieve(release=release, query=message, limit=5)

    messages: list[ChatMessage] = []
    system_prompt = _release_system_prompt(release)
    if system_prompt:
        messages.append(ChatMessage(role="system", content=system_prompt))
    if fragments:
        knowledge = "\n\n".join(
            f"[{fragment.version.document.code}#{fragment.chunk_index}] {fragment.content}" for fragment in fragments
        )
        messages.append(ChatMessage(role="system", content="Отвечай только на основе этих знаний:\n" + knowledge))
    for item in history or []:
        messages.append(ChatMessage(role=str(item.get("role", "user")), content=str(item.get("content", ""))))
    messages.append(ChatMessage(role="user", content=message))

    result = invoke_chat(
        product=release.product,
        messages=messages,
        purpose="test_chat",
        release=release,
        model=release.model,
        params=release.model_params or None,
        used_fragment_ids=[fragment.id for fragment in fragments],
    )

    # ADR-HUB-0007: нет основания в знаниях -> передача оператору.
    return TestChatResult(result=result, fragments=fragments, handoff_suggested=not fragments)
