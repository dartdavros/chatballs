"""Bulk content operations with common validation, selectors and audit."""

from django.core.exceptions import ValidationError

from chatballs.ai.agent_attachments import link_knowledge_to_agent, link_portal_articles_to_agent
from chatballs.ai.knowledge_bulk import add_category_knowledge_to_agent, bulk_move_knowledge
from chatballs.ai.selectors import agent_for_employee
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event


def positive_id(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError({field: t("api.positive_id_required")})
    return value


def ids(body, field):
    raw = body.get(field)
    if not isinstance(raw, list):
        raise ValidationError({field: t("ai.list_of_knowledge_ids" if field == "knowledgeIds" else "ai.list_of_ids")})
    return [positive_id(value, field) for value in raw]


def audit(context, action, object_type, object_id, payload, request):
    record_audit_event(action=action, actor=context.membership.user, organization=context.organization,
        object_type=object_type, object_id=str(object_id), payload=payload, request=request)


def move(context, body, *, request=None):
    selected = ids(body, "knowledgeIds")
    category_id = positive_id(body.get("categoryId"), "categoryId")
    updated = bulk_move_knowledge(context=context, knowledge_ids=selected, category_id=category_id)
    audit(context, "ai.knowledge_bulk_moved", "Knowledge", "", {"knowledgeIds": updated}, request)
    return {"updated": len(updated), "knowledgeIds": updated}


def link(context, body, *, articles=False, request=None):
    agent_id = positive_id(body.get("agentId"), "agentId")
    field = "articleIds" if articles else "knowledgeIds"
    selected = ids(body, field)
    action = str(body.get("action", "attach"))
    if action not in {"attach", "detach"}:
        raise ValidationError({"action": t("ai.expected_attach_or_detach")})
    agent = agent_for_employee(context=context, agent_id=agent_id, capability="ai.manage")
    if articles:
        result = link_portal_articles_to_agent(context=context, agent=agent,
            article_ids=selected, attach=action == "attach")
    else:
        result = link_knowledge_to_agent(context=context, agent=agent,
            knowledge_ids=selected, attach=action == "attach")
    prefix = "ai.agent_portal_articles" if articles else "ai.agent_knowledge"
    audit(context, f"{prefix}_{'attached' if action == 'attach' else 'detached'}", "AIAgent", agent_id,
        {field: list(result.linked_ids)}, request)
    return {"agentId": result.agent_id, "action": action, "changed": len(result.linked_ids),
        "changedIds": list(result.linked_ids), "skippedIds": list(result.skipped_ids),
        field: list(result.selected_ids)}


def select_category(context, agent_id, body, *, request=None):
    agent = agent_for_employee(context=context, agent_id=agent_id, capability="ai.manage")
    category_id = positive_id(body.get("categoryId"), "categoryId")
    result = add_category_knowledge_to_agent(context=context, agent=agent, category_id=category_id)
    audit(context, "ai.agent_category_knowledge_selected", "AIAgent", agent_id,
        {"categoryId": category_id, "addedKnowledgeIds": list(result.added_ids)}, request)
    return {"agentId": agent_id, "categoryId": category_id, "addedKnowledgeIds": list(result.added_ids),
        "knowledgeIds": list(result.selected_ids)}
