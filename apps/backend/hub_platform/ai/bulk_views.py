from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.agent_attachments import (
    AgentLinkResult,
    link_knowledge_to_agent,
    link_portal_articles_to_agent,
)
from hub_platform.ai.api_errors import validation_error_response
from hub_platform.ai.knowledge_bulk import (
    add_category_knowledge_to_agent,
    bulk_move_knowledge,
)
from hub_platform.ai.models import AIAgent
from hub_platform.ai.selectors import agent_for_employee
from hub_platform.api.permissions import HasCapability
from hub_platform.identity.audit import record_audit_event


def _positive_id(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError({field: "Positive integer ID required"})
    return value


def _knowledge_ids(body: dict[str, object]) -> list[int]:
    raw_ids = body.get("knowledgeIds")
    if not isinstance(raw_ids, list):
        raise ValidationError({"knowledgeIds": "List of knowledge IDs required"})
    return [_positive_id(item, "knowledgeIds") for item in raw_ids]


def _audit_bulk(request: Request, action: str, object_ids: list[int]) -> None:
    record_audit_event(
        action=action,
        actor=request.user,
        organization=request.tenant_context.organization,
        object_type="Knowledge",
        object_id="",
        payload={"knowledgeIds": object_ids},
        request=request,
    )


class _KnowledgeBulkView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"


class KnowledgeBulkMoveView(_KnowledgeBulkView):
    def post(self, request: Request) -> Response:
        try:
            knowledge_ids = _knowledge_ids(request.data)
            category_id = _positive_id(request.data.get("categoryId"), "categoryId")
            updated_ids = bulk_move_knowledge(
                context=request.tenant_context,
                knowledge_ids=knowledge_ids,
                category_id=category_id,
            )
        except ValidationError as error:
            return validation_error_response(error)
        _audit_bulk(request, "ai.knowledge_bulk_moved", updated_ids)
        return Response({"updated": len(updated_ids), "knowledgeIds": updated_ids})


def _attach_action(body: dict[str, object]) -> bool:
    action = str(body.get("action", "attach"))
    if action not in {"attach", "detach"}:
        raise ValidationError({"action": "Expected attach or detach"})
    return action == "attach"


class _AgentLinkView(APIView):
    """Массовое прикрепление/открепление одного агента к выборке источников."""

    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    id_field: str
    audit_action: str

    def link(
        self, request: Request, agent: AIAgent, ids: list[int], attach: bool
    ) -> AgentLinkResult:
        raise NotImplementedError

    def post(self, request: Request) -> Response:
        agent_id = None
        try:
            agent_id = _positive_id(request.data.get("agentId"), "agentId")
            raw_ids = request.data.get(self.id_field)
            if not isinstance(raw_ids, list):
                raise ValidationError({self.id_field: "List of IDs required"})
            ids = [_positive_id(item, self.id_field) for item in raw_ids]
            attach = _attach_action(request.data)
        except ValidationError as error:
            return validation_error_response(error)
        try:
            agent = agent_for_employee(
                context=request.tenant_context,
                agent_id=agent_id,
                capability="ai.manage",
            )
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        try:
            result = self.link(request, agent, ids, attach)
        except ValidationError as error:
            return validation_error_response(error)
        record_audit_event(
            action=f"{self.audit_action}_{'attached' if attach else 'detached'}",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="AIAgent",
            object_id=str(agent_id),
            payload={self.id_field: list(result.linked_ids)},
            request=request,
        )
        return Response(
            {
                "agentId": result.agent_id,
                "action": "attach" if attach else "detach",
                "changed": len(result.linked_ids),
                "changedIds": list(result.linked_ids),
                "skippedIds": list(result.skipped_ids),
                self.id_field: list(result.selected_ids),
            }
        )


class AgentKnowledgeLinkView(_AgentLinkView):
    id_field = "knowledgeIds"
    audit_action = "ai.agent_knowledge"

    def link(
        self, request: Request, agent: AIAgent, ids: list[int], attach: bool
    ) -> AgentLinkResult:
        return link_knowledge_to_agent(
            context=request.tenant_context,
            agent=agent,
            knowledge_ids=ids,
            attach=attach,
        )


class AgentPortalArticleLinkView(_AgentLinkView):
    id_field = "articleIds"
    audit_action = "ai.agent_portal_articles"

    def link(
        self, request: Request, agent: AIAgent, ids: list[int], attach: bool
    ) -> AgentLinkResult:
        return link_portal_articles_to_agent(
            context=request.tenant_context,
            agent=agent,
            article_ids=ids,
            attach=attach,
        )


class AgentCategoryKnowledgeSelectView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"

    def post(self, request: Request, agent_id: int) -> Response:
        try:
            agent = agent_for_employee(
                context=request.tenant_context,
                agent_id=agent_id,
                capability="ai.manage",
            )
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        try:
            category_id = _positive_id(request.data.get("categoryId"), "categoryId")
            result = add_category_knowledge_to_agent(
                context=request.tenant_context,
                agent=agent,
                category_id=category_id,
            )
        except ValidationError as error:
            return validation_error_response(error)
        record_audit_event(
            action="ai.agent_category_knowledge_selected",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="AIAgent",
            object_id=str(agent_id),
            payload={
                "categoryId": category_id,
                "addedKnowledgeIds": list(result.added_ids),
            },
            request=request,
        )
        return Response(
            {
                "agentId": agent_id,
                "categoryId": category_id,
                "addedKnowledgeIds": list(result.added_ids),
                "knowledgeIds": list(result.selected_ids),
            }
        )
