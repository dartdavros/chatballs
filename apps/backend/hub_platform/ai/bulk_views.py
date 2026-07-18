from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.api_errors import validation_error_response
from hub_platform.ai.knowledge_bulk import (
    add_category_knowledge_to_agent,
    bulk_move_knowledge,
    bulk_replace_knowledge_visibility,
)
from hub_platform.ai.knowledge_conflicts import KnowledgeScopeConflict
from hub_platform.ai.models import AIAgent
from hub_platform.ai.selectors import agent_for_employee
from hub_platform.api.permissions import HasCapability, HasEntitlement
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


def _department_ids(body: dict[str, object]) -> list[int]:
    raw_ids = body.get("departmentIds", [])
    if not isinstance(raw_ids, list):
        raise ValidationError({"departmentIds": "List of department IDs required"})
    return [_positive_id(item, "departmentIds") for item in raw_ids]


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
    permission_classes = [HasEntitlement, HasCapability]
    required_entitlement = "knowledge_base"
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


class KnowledgeBulkVisibilityView(_KnowledgeBulkView):
    def post(self, request: Request) -> Response:
        try:
            knowledge_ids = _knowledge_ids(request.data)
            updated_ids = bulk_replace_knowledge_visibility(
                context=request.tenant_context,
                knowledge_ids=knowledge_ids,
                visibility=str(request.data.get("visibility", "")),
                department_ids=_department_ids(request.data),
            )
        except KnowledgeScopeConflict as error:
            return Response(error.payload(), status=409)
        except ValidationError as error:
            return validation_error_response(error)
        _audit_bulk(request, "ai.knowledge_bulk_visibility_replaced", updated_ids)
        return Response({"updated": len(updated_ids), "knowledgeIds": updated_ids})


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
