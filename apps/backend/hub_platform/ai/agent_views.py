from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.models import AIAgent, CredentialMode
from hub_platform.ai.selectors import agent_for_context, agents_for_context
from hub_platform.ai.serializers import agent_payload
from hub_platform.ai.services import (
    AgentCreateInput,
    AgentInput,
    create_agent,
    set_agent_active,
    update_agent,
)
from hub_platform.api.permissions import HasCapability
from hub_platform.identity.audit import record_audit_event
from hub_platform.subscriptions.errors import (
    PolicyUnavailable,
    QuotaExceeded,
    SubscriptionDomainError,
)


def _agent_input(body: dict[str, object], *, current: AIAgent) -> AgentInput:
    model_params = body.get("modelParams", current.model_params)
    allowed_tools = body.get("allowedTools", current.allowed_tools)
    limits = body.get("limits", current.limits)
    knowledge_ids = body.get("knowledgeIds")
    if not isinstance(model_params, dict):
        raise ValidationError({"modelParams": "Object required"})
    if not isinstance(allowed_tools, list):
        raise ValidationError({"allowedTools": "List required"})
    if not isinstance(limits, dict):
        raise ValidationError({"limits": "Object required"})
    if knowledge_ids is not None and (
        not isinstance(knowledge_ids, list)
        or not all(isinstance(item, int) for item in knowledge_ids)
    ):
        raise ValidationError({"knowledgeIds": "List of ids required"})
    provider_integration_id = body.get(
        "providerIntegrationId", current.channel.provider_integration_id
    )
    if provider_integration_id is not None and not isinstance(provider_integration_id, int):
        raise ValidationError({"providerIntegrationId": "Integer id required"})
    return AgentInput(
        name=str(body.get("name", current.name)).strip() or current.name,
        credential_mode=str(
            body.get("credentialMode", current.credential_mode)
        ).strip(),
        provider_integration_id=provider_integration_id,
        model_params=model_params,
        allowed_tools=allowed_tools,
        limits=limits,
        persona=str(body.get("persona", current.persona)),
        tone=str(body.get("tone", current.tone)),
        instructions=str(body.get("instructions", current.instructions)),
        knowledge_ids=knowledge_ids,
    )


def _validation_error(error: ValidationError) -> Response:
    detail = (
        "; ".join(message for messages in error.message_dict.values() for message in messages)
        if hasattr(error, "message_dict")
        else "; ".join(error.messages)
    )
    return Response({"detail": detail}, status=400)


class AIAgentListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "ai.view", "POST": "ai.manage"}
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        agents = agents_for_context(request.tenant_context)
        return Response({"items": [agent_payload(agent) for agent in agents]})

    def post(self, request: Request) -> Response:
        knowledge_ids = request.data.get("knowledgeIds", [])
        if not isinstance(knowledge_ids, list) or not all(
            isinstance(item, int) for item in knowledge_ids
        ):
            return Response({"detail": "knowledgeIds must be a list of ids"}, status=400)
        try:
            agent = create_agent(
                context=request.tenant_context,
                data=AgentCreateInput(
                    channel_code=str(request.data.get("channel", "")).strip(),
                    credential_mode=str(
                        request.data.get("credentialMode", CredentialMode.CUSTOAI)
                    ).strip(),
                    provider_integration_id=request.data.get("providerIntegrationId"),
                    persona=str(request.data.get("persona", "")),
                    tone=str(request.data.get("tone", "")),
                    instructions=str(request.data.get("instructions", "")),
                    knowledge_ids=knowledge_ids,
                ),
            )
        except ValidationError as error:
            return _validation_error(error)
        record_audit_event(
            action="ai.agent_created",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="AIAgent",
            object_id=str(agent.id),
            request=request,
        )
        return Response({"agent": agent_payload(agent)}, status=201)


class AIAgentDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.view"
    require_organization_scope = True

    def get(self, request: Request, agent_id: int) -> Response:
        try:
            agent = agent_for_context(context=request.tenant_context, agent_id=agent_id)
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        return Response({"agent": agent_payload(agent)})


class AIAgentUpdateView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    require_organization_scope = True

    def patch(self, request: Request, agent_id: int) -> Response:
        try:
            agent = agent_for_context(context=request.tenant_context, agent_id=agent_id)
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        try:
            agent = update_agent(
                context=request.tenant_context,
                agent=agent,
                data=_agent_input(request.data, current=agent),
            )
        except ValidationError as error:
            return _validation_error(error)
        record_audit_event(
            action="ai.agent_updated",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="AIAgent",
            object_id=str(agent.id),
            request=request,
        )
        return Response(
            {
                "agent": agent_payload(
                    agent_for_context(context=request.tenant_context, agent_id=agent_id)
                )
            }
        )


class _AIAgentStatusView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    require_organization_scope = True
    target_active: bool

    def post(self, request: Request, agent_id: int) -> Response:
        try:
            agent = agent_for_context(context=request.tenant_context, agent_id=agent_id)
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        try:
            agent = set_agent_active(
                context=request.tenant_context,
                agent=agent,
                is_active=self.target_active,
            )
        except QuotaExceeded as error:
            return Response(
                {
                    "code": error.code,
                    "resource": error.resource,
                    "limit": error.limit,
                    "used": error.used,
                    "requested": error.requested,
                    "period_ends_at": (
                        error.period_ends_at.isoformat() if error.period_ends_at else None
                    ),
                },
                status=409,
            )
        except PolicyUnavailable as error:
            return Response({"code": error.code}, status=503)
        except SubscriptionDomainError as error:
            return Response({"code": error.code}, status=409)
        return Response({"agent": agent_payload(agent)})


class AIAgentActivateView(_AIAgentStatusView):
    target_active = True


class AIAgentDeactivateView(_AIAgentStatusView):
    target_active = False
