from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.models import AIAgent
from hub_platform.ai.selectors import agent_for_organization, agents_for_organization
from hub_platform.ai.serializers import agent_payload
from hub_platform.ai.services import AgentInput, set_agent_active, update_agent
from hub_platform.api.permissions import IsOwner
from hub_platform.identity.audit import record_audit_event


def _agent_input(body: dict[str, object], *, current: AIAgent) -> AgentInput:
    model_params = body.get("modelParams", current.model_params)
    allowed_tools = body.get("allowedTools", current.allowed_tools)
    limits = body.get("limits", current.limits)
    if not isinstance(model_params, dict):
        raise ValidationError({"modelParams": "Object required"})
    if not isinstance(allowed_tools, list):
        raise ValidationError({"allowedTools": "List required"})
    if not isinstance(limits, dict):
        raise ValidationError({"limits": "Object required"})
    return AgentInput(
        name=str(body.get("name", current.name)).strip() or current.name,
        model=str(body.get("model", current.model)).strip() or current.model,
        model_params=model_params,
        allowed_tools=allowed_tools,
        limits=limits,
    )


def _validation_error(error: ValidationError) -> Response:
    detail = "; ".join(message for messages in error.message_dict.values() for message in messages) if hasattr(error, "message_dict") else "; ".join(error.messages)
    return Response({"detail": detail}, status=400)


class AIAgentListView(APIView):
    permission_classes = [IsOwner]

    def get(self, request: Request) -> Response:
        agents = agents_for_organization(request.user.employee_profile.organization_id)
        return Response({"items": [agent_payload(agent) for agent in agents]})


class AIAgentDetailView(APIView):
    permission_classes = [IsOwner]

    def get(self, request: Request, agent_id: int) -> Response:
        try:
            agent = agent_for_organization(organization_id=request.user.employee_profile.organization_id, agent_id=agent_id)
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        return Response({"agent": agent_payload(agent)})


class AIAgentUpdateView(APIView):
    permission_classes = [IsOwner]

    def patch(self, request: Request, agent_id: int) -> Response:
        organization_id = request.user.employee_profile.organization_id
        try:
            agent = agent_for_organization(organization_id=organization_id, agent_id=agent_id)
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        try:
            agent = update_agent(agent=agent, data=_agent_input(request.data, current=agent))
        except ValidationError as error:
            return _validation_error(error)
        record_audit_event(
            action="ai.agent_updated",
            actor=request.user,
            organization=request.user.employee_profile.organization,
            object_type="AIAgent",
            object_id=str(agent.id),
            request=request,
        )
        return Response({"agent": agent_payload(agent)})


class _AIAgentStatusView(APIView):
    permission_classes = [IsOwner]
    target_active: bool

    def post(self, request: Request, agent_id: int) -> Response:
        organization = request.user.employee_profile.organization
        try:
            agent = agent_for_organization(organization_id=organization.id, agent_id=agent_id)
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        agent = set_agent_active(agent=agent, is_active=self.target_active)
        record_audit_event(
            action="ai.agent_activated" if self.target_active else "ai.agent_deactivated",
            actor=request.user,
            organization=organization,
            object_type="AIAgent",
            object_id=str(agent.id),
            request=request,
        )
        return Response({"agent": agent_payload(agent)})


class AIAgentActivateView(_AIAgentStatusView):
    target_active = True


class AIAgentDeactivateView(_AIAgentStatusView):
    target_active = False
