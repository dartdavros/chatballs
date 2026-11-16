from dataclasses import dataclass

from chatballs.ai.agent_knowledge import (
    runtime_knowledge_for_agent,
    runtime_portal_articles_for_agent,
)
from chatballs.ai.invocation import invoke_chat
from chatballs.ai.models import AIAgent, AnswerLanguage, KnowledgeFragment
from chatballs.ai.provider.base import ChatMessage, ChatResult
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.ai.retrieval import KnowledgeRetriever
from chatballs.ai.site_context import customer_data_prompt
from chatballs.conversations.models import Conversation
from chatballs.i18n import LANGUAGES, customer_language, normalize_language
from chatballs.support_portals.addressing import article_public_url

# Название языка — на нём самом: модели так однозначнее, чем «английский».
LANGUAGE_LABELS = dict(LANGUAGES)

# Гард стиля для мессенджеров: гарантирует простой текст вне зависимости от
# того, что написано в авторских инструкциях.
MESSENGER_STYLE_GUARD = (
    "Пиши ответ простым текстом для мессенджера: без markdown-разметки — "
    "никаких **, ##, маркированных списков с -, таблиц, ссылок вида [текст](url). "
    "Короткие абзацы. Не придумывай факты, контакты, ссылки, цены и условия, "
    "которых нет в знаниях; если данных нет — честно скажи и предложи оператора."
)

# Протокол передачи оператору: модель добавляет технический токен, система его
# ловит, ставит диалог в очередь и уведомляет операторов (ADR-CHATBALLS-0003).
HANDOFF_TOKEN = "<<HANDOFF>>"
HANDOFF_PROTOCOL = (
    "Если по правилам нужно подключить живого оператора (клиент просит человека; "
    "вопрос вне базы знаний; индивидуальные условия, скидка, счёт, оплата от юрлица, "
    "документы; жалоба, спор или проблема с оплатой/доступом), в самом конце ответа "
    f"добавь отдельной строкой технический токен {HANDOFF_TOKEN}. Не упоминай этот "
    "токен в тексте и не показывай его пользователю — просто заверши им сообщение."
)

# Токены псевдонимизации (SPEC-0022 R-8). Директива не переводится и уходит
# модели как есть: образец токена в ней не должен экранироваться.
TOKEN_DIRECTIVE = (
    "Персональные данные в этом диалоге заменены токенами в двойных квадратных "
    "скобках, например [[имя_токена]]. Перед отправкой клиенту система сама "
    "подставит вместо токена настоящее значение. Переписывай токены в ответ без "
    "изменений: не склоняй, не переводи, не сокращай и не меняй скобки. Не пытайся "
    "угадать значения за токенами и не придумывай токены, которых нет в диалоге. "
    "Если в данных клиента есть имя, обращайся к клиенту токеном имени: без "
    "склонения и без предположений о поле клиента."
)


# Язык ответа. Директива стоит отдельной строкой и последней среди системных:
# промпт написан по-русски и сам по себе тянет ответ в русский язык, а явное
# указание это перебивает. Переводить сам промпт не нужно — его читает модель,
# а не человек.
ANSWER_IN_CUSTOMER_LANGUAGE = (
    "Отвечай на том языке, на котором написано последнее сообщение клиента. "
    "Если язык определить не удалось, отвечай на языке предыдущей переписки."
)
ANSWER_IN_FIXED_LANGUAGE = (
    "Отвечай всегда на языке «{language}», независимо от того, на каком языке "
    "написал клиент."
)


def answer_language_directive(agent: AIAgent) -> str:
    """Строка системного промпта, задающая язык ответа агента."""

    if agent.answer_language == AnswerLanguage.MIRROR:
        return ANSWER_IN_CUSTOMER_LANGUAGE
    if agent.answer_language == AnswerLanguage.ORGANIZATION:
        code = customer_language(agent.channel.organization)
    else:
        code = normalize_language(agent.answer_language)
    if not code:
        # Код испортили руками или язык убрали из сборки: зеркало клиента
        # безопаснее молчания — ответ всё равно попадёт в язык обращения.
        return ANSWER_IN_CUSTOMER_LANGUAGE
    return ANSWER_IN_FIXED_LANGUAGE.format(language=LANGUAGE_LABELS[code])


@dataclass(frozen=True)
class AgentTurnResult:
    result: ChatResult
    fragments: list[KnowledgeFragment]
    handoff_suggested: bool


def agent_system_prompt(agent: AIAgent) -> str:
    # Порядок частей фиксирован (ADR-CHATBALLS-0023): Персонализация -> Тон -> Инструкции.
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


def build_turn_messages(
    *,
    agent: AIAgent,
    message: str,
    history: list[dict] | None = None,
    fragments: list[KnowledgeFragment],
    style_guard: bool = True,
    conversation: Conversation | None = None,
    pseudonymizer: Pseudonymizer | None = None,
) -> list[ChatMessage]:
    """Промпт хода целиком: инструкции агента, каталог знаний, найденное, история.

    Только чтение базы и склейка строк — обращений наружу здесь нет, поэтому
    сборку можно держать внутри транзакции (chatballs.ai.turn).

    Блок «Данные клиента» собирается с токенами карты хода, поэтому карту
    передают ту же, которой потом маскируется весь запрос; без неё блока нет.
    """
    messages: list[ChatMessage] = []
    system_prompt = agent_system_prompt(agent)
    if system_prompt:
        messages.append(ChatMessage(role="system", content=system_prompt))
    customer_data = (
        customer_data_prompt(conversation, pseudonymizer) if pseudonymizer is not None else ""
    )
    if customer_data:
        messages.append(ChatMessage(role="system", content=customer_data, masked=True))
    messages.append(ChatMessage(role="system", content=TOKEN_DIRECTIVE, masked=True))
    if style_guard:
        messages.append(
            ChatMessage(role="system", content=MESSENGER_STYLE_GUARD + "\n\n" + HANDOFF_PROTOCOL)
        )
    messages.append(ChatMessage(role="system", content=answer_language_directive(agent)))
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
    return messages


def run_agent_turn(
    *,
    agent: AIAgent,
    message: str,
    history: list[dict] | None = None,
    style_guard: bool = True,
) -> AgentTurnResult:
    """Ход агента целиком, в транзакции вызывающего.

    Остаётся для мест, где ждать провайдера под транзакцией не жалко:
    предпросмотр на карточке агента и тесты. Ход диалога с клиентом идёт
    шагами, вне транзакции (chatballs.ai.turn).
    """
    # Диалога здесь нет, известных значений тоже: одна карта на вектор вопроса
    # и на запрос к модели маскирует найденное шаблонами.
    from chatballs.ai.external_agents.readiness import require_builtin

    require_builtin(agent)
    pseudonymizer = Pseudonymizer()
    fragments = KnowledgeRetriever().retrieve(
        agent=agent, query=message, limit=5, pseudonymizer=pseudonymizer
    )
    messages = build_turn_messages(
        agent=agent,
        message=message,
        history=history,
        fragments=fragments,
        style_guard=style_guard,
        pseudonymizer=pseudonymizer,
    )
    result = invoke_chat(
        channel=agent.channel,
        messages=messages,
        purpose="agent_chat",
        model=agent.model,
        params=agent.model_params or None,
        used_fragment_ids=[fragment.id for fragment in fragments],
        pseudonymizer=pseudonymizer,
    )

    # Нет основания в знаниях -> кандидат на передачу оператору (ADR-CHATBALLS-0003).
    return AgentTurnResult(result=result, fragments=fragments, handoff_suggested=not fragments)
