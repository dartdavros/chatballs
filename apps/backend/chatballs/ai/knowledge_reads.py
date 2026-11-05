"""Knowledge read application services shared by HTTP and automation."""

from chatballs.ai.selectors import (
    apply_knowledge_filters,
    knowledge_editors,
    knowledge_for_context,
    knowledge_item_for_context,
)
from chatballs.ai.serializers import knowledge_payload
from chatballs.api.pagination import page_payload, paginate
from chatballs.identity.models import AuditEvent


def list_knowledge(context, filters, params):
    page = paginate(apply_knowledge_filters(knowledge_for_context(context), filters,
        organization_id=context.organization_id), params, default_size=25)
    editors = knowledge_editors(organization_id=context.organization_id,
        knowledge_ids=[item.id for item in page.items])

    def payload(item):
        data = knowledge_payload(item, include_content=False)
        if editor := editors.get(item.id):
            data["updatedBy"] = editor
        return data

    return page_payload(page, payload)


def get_knowledge(context, knowledge_id):
    knowledge = knowledge_item_for_context(context=context, knowledge_id=knowledge_id)
    payload = knowledge_payload(knowledge)
    event = AuditEvent.objects.filter(organization_id=context.organization_id,
        action="ai.knowledge_created", object_type="Knowledge", object_id=str(knowledge.id)
        ).select_related("actor").order_by("created_at").first()
    if event and event.actor:
        payload["createdBy"] = event.actor.full_name or event.actor.email
    if editor := knowledge_editors(organization_id=context.organization_id,
            knowledge_ids=[knowledge.id]).get(knowledge.id):
        payload["updatedBy"] = editor
    payload["agents"] = [{"id": agent.id, "name": agent.channel.name,
        "groupName": agent.channel.group.name if agent.channel.group_id else None,
        "aiStatus": agent.status} for agent in knowledge.agents.select_related(
            "channel", "channel__group").order_by("channel__name")]
    return {"knowledge": payload}
