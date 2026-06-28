from dataclasses import dataclass

from hub_platform.ai.invocation import invoke_chat
from hub_platform.ai.models import KnowledgeFragment, ChannelAIRelease, PromptCategory
from hub_platform.ai.provider.base import ChatMessage, ChatResult
from hub_platform.ai.retrieval import KnowledgeRetriever

_PROMPT_ORDER = [
    PromptCategory.SYSTEM,
    PromptCategory.QUALIFICATION,
    PromptCategory.SALES_BEHAVIOR,
    PromptCategory.OPERATOR_HANDOFF,
]

# Гард стиля для мессенджеров: гарантирует простой текст вне зависимости от
# того, что написано в авторских промптах.
MESSENGER_STYLE_GUARD = (
    "Пиши ответ простым текстом для мессенджера: без markdown-разметки — "
    "никаких **, ##, маркированных списков с -, таблиц, ссылок вида [текст](url). "
    "Короткие абзацы. Не придумывай факты, контакты, ссылки, цены и условия, "
    "которых нет в знаниях; если данных нет — честно скажи и предложи оператора."
)

# Протокол передачи оператору: модель добавляет технический токен, система его
# ловит, ставит диалог в очередь и уведомляет операторов (ADR-HUB-0003).
HANDOFF_TOKEN = "<<HANDOFF>>"
HANDOFF_PROTOCOL = (
    "Если по правилам нужно подключить живого оператора (клиент просит человека; "
    "вопрос вне базы знаний; индивидуальные условия, скидка, счёт, оплата от юрлица, "
    "документы; жалоба, спор или проблема с оплатой/доступом), в самом конце ответа "
    f"добавь отдельной строкой технический токен {HANDOFF_TOKEN}. Не упоминай этот "
    "токен в тексте и не показывай его пользователю — просто заверши им сообщение."
)


@dataclass(frozen=True)
class TestChatResult:
    result: ChatResult
    fragments: list[KnowledgeFragment]
    handoff_suggested: bool


def _release_system_prompt(release: ChannelAIRelease) -> str:
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


def run_test_chat(*, release: ChannelAIRelease, message: str, history: list[dict] | None = None, style_guard: bool = False) -> TestChatResult:
    fragments = KnowledgeRetriever().retrieve(release=release, query=message, limit=5)

    messages: list[ChatMessage] = []
    system_prompt = _release_system_prompt(release)
    if system_prompt:
        messages.append(ChatMessage(role="system", content=system_prompt))
    if style_guard:
        messages.append(ChatMessage(role="system", content=MESSENGER_STYLE_GUARD + "\n\n" + HANDOFF_PROTOCOL))
    if fragments:
        knowledge = "\n\n".join(
            f"[{fragment.version.document.code}#{fragment.chunk_index}] {fragment.content}" for fragment in fragments
        )
        messages.append(ChatMessage(role="system", content="Отвечай только на основе этих знаний:\n" + knowledge))
    for item in history or []:
        messages.append(ChatMessage(role=str(item.get("role", "user")), content=str(item.get("content", ""))))
    messages.append(ChatMessage(role="user", content=message))

    result = invoke_chat(
        channel=release.channel,
        messages=messages,
        purpose="test_chat",
        release=release,
        model=release.model,
        params=release.model_params or None,
        used_fragment_ids=[fragment.id for fragment in fragments],
    )

    # ADR-HUB-0007: нет основания в знаниях -> передача оператору.
    return TestChatResult(result=result, fragments=fragments, handoff_suggested=not fragments)
