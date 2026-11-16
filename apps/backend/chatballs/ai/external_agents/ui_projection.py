"""Scoped, allowlisted operational state; never open a recovery payload for UI."""

from django.utils import timezone

from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.notice_models import ExternalAgentNotice
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.state import FINAL, applicable
from chatballs.tenancy.context import TenantContext


def message_status(message):
    if message.system_event == "returned_to_ai" and message.system_params.get("externalExecution") is True:
        return {"externalReturned": True}
    if message.kind == "voice" and message.transcript_status == "READY" and ExternalAgentRequest.objects.filter(
        trigger_id=message.pk, organization_id=message.organization_id,
    ).exists():
        return {"externalVoice": "ready"}
    item = getattr(message, "externalagentdeliveryitem", None)
    fact = message.ai_delivery.get("externalDelivery")
    if item is None and not fact:
        return {}
    state = item.state if item else fact["state"]
    state = state if state in {"queued", "transport_accepted", "unknown", "failed", "suppressed"} else "unknown"
    return {"externalDelivery": {"state": state,
            "textFallback": bool(message.template_snapshot and message.delivery_representation == "text"),
            "initiative": item.delivery.request.trigger_id is None if item else fact["initiative"]}}


def conversation_status(conversation):
    notices = [{"id": f"notice:{notice.pk}", "kind": notice.kind,
                "summary": notice.summary, "createdAt": notice.created_at.isoformat()}
               for notice in ExternalAgentNotice.objects.filter(
                   conversation=conversation, organization_id=conversation.organization_id,
                   kind__in=["handoff", "unavailable", "timeout", "voiceFailure", "suppressed"],
               ).order_by("-pk")[:100]]
    row = ExternalAgentRequest.objects.filter(conversation=conversation,
        organization_id=conversation.organization_id).select_related("session__agent__external_binding").order_by("-pk").first()
    waiting = None
    if row:
        states = list(ExternalAgentDeliveryItem.objects.filter(delivery__request=row).values_list("state", flat=True))
        if "unknown" in states or ExternalAgentDeliveryItem.objects.filter(delivery__request=row, sending=True).exists():
            notices.append({"id": f"delivery:{row.pk}", "kind": "partial" if "transport_accepted" in states else "unknown",
                            "summary": "", "createdAt": (row.terminal_at or row.created_at).isoformat()})
        if row.state not in FINAL and row.state != "delivering" and applicable(row, TenantContext.for_resource(conversation.organization)):
            waiting = "long" if (timezone.now() - row.created_at).total_seconds() > row.session.agent.external_binding.ordinary_timeout else "ordinary"
    return {"notices": sorted(notices, key=lambda item: item["createdAt"]), "waiting": waiting}
