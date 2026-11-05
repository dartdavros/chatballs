"""Agent directory and card reads shared by HTTP and native actions."""

from django.db.models import Count, Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from chatballs.ai.agent_card import (
    agent_card_for_context,
    agent_card_payload,
    agent_cards_for_context,
    knowledge_total_for_organization,
)
from chatballs.ai.agent_tools import agent_tools_payload
from chatballs.api.pagination import page_payload, paginate
from chatballs.i18n import t
from chatballs.identity.policy import has_capability_any_scope

AGENT_DIRECTORY_LIMIT = 200


def require(context, capability="ai.view"):
    if not has_capability_any_scope(context.membership, capability):
        raise PermissionDenied()


def _searched(context, params):
    require(context)
    cards = agent_cards_for_context(context)
    query = params.get("q", "").strip()
    return cards.filter(Q(name__icontains=query) | Q(code__icontains=query)) if query else cards


def directory(context, params):
    cards = _searched(context, params).annotate(
        knowledge_count=Count("ai_agent__knowledge_items", distinct=True))
    items = [{"id": channel.id, "aiAgentId": channel.ai_agent.id,
        "name": channel.name, "groupName": channel.group.name if channel.group_id else None,
        "aiStatus": channel.ai_agent.status, "isActive": channel.is_active,
        "knowledgeCount": channel.knowledge_count}
        for channel in cards.order_by("name")[:AGENT_DIRECTORY_LIMIT + 1]]
    return {"items": items[:AGENT_DIRECTORY_LIMIT], "hasMore": len(items) > AGENT_DIRECTORY_LIMIT}


def listing(context, params):
    cards = _searched(context, params)
    group = params.get("group")
    if group == "none":
        cards = cards.filter(group__isnull=True)
    elif group:
        try:
            cards = cards.filter(group_id=int(group))
        except (TypeError, ValueError):
            raise ValidationError({"detail": t("ai.group_id_or_none")}) from None
    total = knowledge_total_for_organization(context.organization_id)
    return page_payload(paginate(cards, params), lambda channel:
        agent_card_payload(channel, knowledge_total=total, with_tools=False))


def detail(context, agent_id):
    require(context)
    channel = agent_card_for_context(context=context, agent_id=agent_id)
    return {"agent": agent_card_payload(channel, check_tool_support=True)}


def tools(context, agent_id):
    require(context)
    channel = agent_card_for_context(context=context, agent_id=agent_id)
    return {"tools": agent_tools_payload(channel.ai_agent)}
