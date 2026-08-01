from dataclasses import dataclass

from hub_platform.ai.agent_knowledge import (
    runtime_knowledge_for_agent,
    runtime_portal_articles_for_agent,
)
from hub_platform.ai.invocation import invoke_chat
from hub_platform.ai.models import AIAgent, KnowledgeFragment
from hub_platform.ai.provider.base import ChatMessage, ChatResult
from hub_platform.ai.retrieval import KnowledgeRetriever
from hub_platform.support_portals.addressing import article_public_url

# Гард стиля для мессенджеров: гарантирует простой текст вне зависимости от
# того, что написано в авторских инструкциях.
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
class AgentTurnResult:
    result: ChatResult
    fragments: list[KnowledgeFragment]
    handoff_suggested: bool


def agent_system_prompt(agent: AIAgent) -> str:
    # Порядок частей фиксирован (ADR-HUB-0023): Персонализация -> Тон -> Инструкции.
    parts = [
        part.strip() for part in (agent.persona, agent.tone, agent.instructions) if part.strip()
    ]
    return "\n\n".join(parts)


def knowledge_catalog(agent: AIAgent) -> str:
    """Каталог выбранных знаний для системного промпта: заголовок, краткое
    описание и публичные ссылки вложений (агент может отдать ссылку клиенту).
    Статьи портала поддержки идут отдельной секцией со ссылкой на Help Center."""
    lines: list[str] = []
    items = runtime_knowledge_for_agent(agent).prefetch_related("attachments")
    for knowledge in items:
        line = f"- {knowledge.title}"
        if knowledge.description.strip():
            line += f" — {knowledge.description.strip()}"
        lines.append(line)
        for attachment in knowledge.attachments.all():
            lines.append(f"  файл: {attachment.original_name} — {attachment.public_url()}")
    article_lines: list[str] = []
    articles = runtime_portal_articles_for_agent(agent).select_related(
        "portal", "published_revision"
    )
    for article in articles:
        revision = article.published_revision
        line = f"- {revision.title}"
        if revision.summary.strip():
            line += f" — {revision.summary.strip()}"
        article_lines.append(f"{line}\n  статья: {article_public_url(article)}")
    if not lines and not article_lines:
        return ""
    parts: list[str] = []
    if lines:
        parts.append(
            "Тебе доступны следующие знания (детали подтягиваются автоматически по "
            "запросу). Ссылки на файлы можно давать клиенту:\n" + "\n".join(lines)
        )
    if article_lines:
        parts.append(
            "Статьи базы знаний поддержки (ссылку можно дать клиенту):\n"
            + "\n".join(article_lines)
        )
    return "\n\n".join(parts)


def run_agent_turn(
    *,
    agent: AIAgent,
    message: str,
    history: list[dict] | None = None,
    style_guard: bool = True,
) -> AgentTurnResult:
    fragments = KnowledgeRetriever().retrieve(agent=agent, query=message, limit=5)

    messages: list[ChatMessage] = []
    system_prompt = agent_system_prompt(agent)
    if system_prompt:
        messages.append(ChatMessage(role="system", content=system_prompt))
    if style_guard:
        messages.append(
            ChatMessage(role="system", content=MESSENGER_STYLE_GUARD + "\n\n" + HANDOFF_PROTOCOL)
        )
    catalog = knowledge_catalog(agent)
    if catalog:
        messages.append(ChatMessage(role="system", content=catalog))
    if fragments:
        knowledge = "\n\n".join(
            f"[{fragment.source_title}#{fragment.chunk_index}] {fragment.content}"
            for fragment in fragments
        )
        messages.append(
            ChatMessage(
                role="system",
                content="Отвечай только на основе этих знаний:\n" + knowledge,
            )
        )
    for item in history or []:
        messages.append(
            ChatMessage(role=str(item.get("role", "user")), content=str(item.get("content", "")))
        )
    messages.append(ChatMessage(role="user", content=message))

    result = invoke_chat(
        channel=agent.channel,
        messages=messages,
        purpose="agent_chat",
        model=agent.model,
        params=agent.model_params or None,
        used_fragment_ids=[fragment.id for fragment in fragments],
    )

    # Нет основания в знаниях -> кандидат на передачу оператору (ADR-HUB-0003).
    return AgentTurnResult(result=result, fragments=fragments, handoff_suggested=not fragments)
