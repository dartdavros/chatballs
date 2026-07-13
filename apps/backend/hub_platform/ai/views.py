from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.models import AIAgent, Knowledge, KnowledgeAttachment
from hub_platform.ai.selectors import (
    agent_for_organization,
    agents_for_organization,
    knowledge_for_organization,
    knowledge_item_for_organization,
)
from hub_platform.ai.serializers import agent_payload, attachment_payload, knowledge_payload
from hub_platform.ai.services import (
    AgentCreateInput,
    AgentInput,
    KnowledgeInput,
    add_attachment,
    create_agent,
    create_knowledge,
    delete_attachment,
    delete_knowledge,
    set_agent_active,
    update_agent,
    update_knowledge,
)
from hub_platform.api.permissions import HasCapability
from hub_platform.identity.audit import record_audit_event


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
    if knowledge_ids is not None and (not isinstance(knowledge_ids, list) or not all(isinstance(item, int) for item in knowledge_ids)):
        raise ValidationError({"knowledgeIds": "List of ids required"})
    return AgentInput(
        name=str(body.get("name", current.name)).strip() or current.name,
        model=str(body.get("model", current.model)).strip() or current.model,
        model_params=model_params,
        allowed_tools=allowed_tools,
        limits=limits,
        persona=str(body.get("persona", current.persona)),
        tone=str(body.get("tone", current.tone)),
        instructions=str(body.get("instructions", current.instructions)),
        knowledge_ids=knowledge_ids,
    )


def _validation_error(error: ValidationError) -> Response:
    detail = "; ".join(message for messages in error.message_dict.values() for message in messages) if hasattr(error, "message_dict") else "; ".join(error.messages)
    return Response({"detail": detail}, status=400)


class AIAgentListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "ai.view", "POST": "ai.manage"}
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        agents = agents_for_organization(request.user.employee_profile.organization_id)
        return Response({"items": [agent_payload(agent) for agent in agents]})

    def post(self, request: Request) -> Response:
        knowledge_ids = request.data.get("knowledgeIds", [])
        if not isinstance(knowledge_ids, list) or not all(isinstance(item, int) for item in knowledge_ids):
            return Response({"detail": "knowledgeIds must be a list of ids"}, status=400)
        try:
            agent = create_agent(
                organization=request.user.employee_profile.organization,
                data=AgentCreateInput(
                    channel_code=str(request.data.get("channel", "")).strip(),
                    model=str(request.data.get("model", "")).strip(),
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
            organization=request.user.employee_profile.organization,
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
            agent = agent_for_organization(organization_id=request.user.employee_profile.organization_id, agent_id=agent_id)
        except AIAgent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=404)
        return Response({"agent": agent_payload(agent)})


class AIAgentUpdateView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    require_organization_scope = True

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
        agent = agent_for_organization(organization_id=organization_id, agent_id=agent_id)
        return Response({"agent": agent_payload(agent)})


class _AIAgentStatusView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"
    require_organization_scope = True
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


# --- Знания (ADR-HUB-0023) ---


def _knowledge_input(body: dict[str, object], *, current: Knowledge | None = None) -> KnowledgeInput:
    is_enabled = body.get("isEnabled", current.is_enabled if current else True)
    return KnowledgeInput(
        title=str(body.get("title", current.title if current else "")),
        description=str(body.get("description", current.description if current else "")),
        content=str(body.get("content", current.content if current else "")),
        is_enabled=bool(is_enabled),
    )


class _KnowledgeBaseView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "ai.view",
        "POST": "ai.manage",
        "PATCH": "ai.manage",
        "DELETE": "ai.manage",
    }
    require_organization_scope = True

    def _org(self, request: Request):
        return request.user.employee_profile.organization

    def _knowledge(self, request: Request, knowledge_id: int) -> Knowledge:
        return knowledge_item_for_organization(organization_id=self._org(request).id, knowledge_id=knowledge_id)

    def _audit(self, request: Request, action: str, knowledge: Knowledge) -> None:
        record_audit_event(
            action=f"ai.knowledge_{action}",
            actor=request.user,
            organization=self._org(request),
            object_type="Knowledge",
            object_id=str(knowledge.id),
            request=request,
        )


class KnowledgeListCreateView(_KnowledgeBaseView):
    def get(self, request: Request) -> Response:
        items = knowledge_for_organization(self._org(request).id)
        return Response({"items": [knowledge_payload(item, include_content=False) for item in items]})

    def post(self, request: Request) -> Response:
        try:
            knowledge = create_knowledge(organization=self._org(request), data=_knowledge_input(request.data))
        except ValidationError as error:
            return _validation_error(error)
        knowledge = self._knowledge(request, knowledge.id)
        self._audit(request, "created", knowledge)
        return Response({"knowledge": knowledge_payload(knowledge)}, status=201)


class KnowledgeDetailView(_KnowledgeBaseView):
    def get(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        return Response({"knowledge": knowledge_payload(knowledge)})

    def patch(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        try:
            knowledge = update_knowledge(knowledge=knowledge, data=_knowledge_input(request.data, current=knowledge))
        except ValidationError as error:
            return _validation_error(error)
        knowledge = self._knowledge(request, knowledge_id)
        self._audit(request, "updated", knowledge)
        return Response({"knowledge": knowledge_payload(knowledge)})

    def delete(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        self._audit(request, "deleted", knowledge)
        delete_knowledge(knowledge=knowledge)
        return Response(status=204)


class KnowledgeImportView(_KnowledgeBaseView):
    # POST {documents: [{title, description?, content}]} — идемпотентный upsert
    # по заголовку (SPEC-HUB-0012). Ошибки per-doc копятся в failed[].
    def post(self, request: Request) -> Response:
        documents = request.data.get("documents")
        if not isinstance(documents, list) or not documents:
            return Response({"detail": "documents must be a non-empty list"}, status=400)
        organization = self._org(request)
        created = updated = unchanged = 0
        failed: list[dict[str, str]] = []
        for index, item in enumerate(documents):
            title = str(item.get("title", "")).strip() if isinstance(item, dict) else ""
            if not title:
                failed.append({"title": "", "detail": f"Документ #{index + 1}: пустой заголовок"})
                continue
            description = str(item.get("description", "") or "").strip()
            content = str(item.get("content", "") or "")
            knowledge = Knowledge.objects.filter(organization=organization, title=title).first()
            if knowledge is None:
                create_knowledge(
                    organization=organization,
                    data=KnowledgeInput(title=title, description=description, content=content, is_enabled=True),
                )
                created += 1
            elif knowledge.content == content and knowledge.description == (description or knowledge.description):
                unchanged += 1
            else:
                update_knowledge(
                    knowledge=knowledge,
                    data=KnowledgeInput(
                        title=title,
                        description=description or knowledge.description,
                        content=content,
                        is_enabled=knowledge.is_enabled,
                    ),
                )
                updated += 1
        record_audit_event(
            action="ai.knowledge_imported",
            actor=request.user,
            organization=organization,
            object_type="Knowledge",
            object_id="",
            payload={"created": created, "updated": updated, "unchanged": unchanged, "failed": failed},
            request=request,
        )
        return Response({"created": created, "updated": updated, "unchanged": unchanged, "failed": failed}, status=201)


class KnowledgeAttachmentUploadView(_KnowledgeBaseView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "file is required (multipart/form-data)"}, status=400)
        try:
            attachment = add_attachment(knowledge=knowledge, upload=upload)
        except ValidationError as error:
            return _validation_error(error)
        self._audit(request, "attachment_added", knowledge)
        return Response({"attachment": attachment_payload(attachment)}, status=201)


class KnowledgeAttachmentDeleteView(_KnowledgeBaseView):
    def delete(self, request: Request, knowledge_id: int, attachment_id: int) -> Response:
        try:
            knowledge = self._knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        attachment = knowledge.attachments.filter(id=attachment_id).first()
        if attachment is None:
            return Response({"detail": "Attachment not found"}, status=404)
        delete_attachment(attachment=attachment)
        self._audit(request, "attachment_deleted", knowledge)
        return Response(status=204)


class AttachmentDownloadView(APIView):
    # Публичная ссылка (ADR-HUB-0023): уходит клиентам в мессенджеры, где нет
    # аутентификации Hub. Защита — непредсказуемый UUID.
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request: Request, public_id) -> FileResponse:
        attachment = KnowledgeAttachment.objects.filter(public_id=public_id).first()
        if attachment is None:
            raise Http404
        return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.original_name)
