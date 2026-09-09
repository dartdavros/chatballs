from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai.api_errors import validation_error_response
from chatballs.ai.indexing import reindex_knowledge
from chatballs.ai.knowledge_api_inputs import knowledge_filters, knowledge_input
from chatballs.ai.knowledge_import import import_knowledge_documents
from chatballs.ai.knowledge_policy import (
    employee_can_write_knowledge,
    require_knowledge_create,
)
from chatballs.ai.knowledge_services import (
    add_attachment,
    create_knowledge,
    delete_attachment,
    delete_knowledge,
    update_knowledge,
)
from chatballs.ai.models import Knowledge
from chatballs.ai.selectors import (
    apply_knowledge_filters,
    knowledge_editors,
    knowledge_for_context,
    knowledge_item_for_context,
    writable_knowledge_item_for_employee,
)
from chatballs.ai.serializers import attachment_payload, knowledge_payload
from chatballs.api.pagination import page_payload, paginate
from chatballs.api.permissions import HasCapability
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import AuditEvent

# Библиотека знаний плотная — своя страница (кадр KB1).
KNOWLEDGE_PAGE_SIZE = 25

_validation_error = validation_error_response


class _KnowledgeBaseView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "ai.view",
        "POST": "ai.manage",
        "PATCH": "ai.manage",
        "DELETE": "ai.manage",
    }

    def _org(self, request: Request):
        return request.tenant_context.organization

    def _read_knowledge(self, request: Request, knowledge_id: int) -> Knowledge:
        return knowledge_item_for_context(context=request.tenant_context, knowledge_id=knowledge_id)

    def _write_knowledge(self, request: Request, knowledge_id: int) -> Knowledge:
        return writable_knowledge_item_for_employee(
            context=request.tenant_context,
            knowledge_id=knowledge_id,
        )

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
        try:
            filters = knowledge_filters(request)
        except ValidationError as error:
            return _validation_error(error)
        page = paginate(
            apply_knowledge_filters(
                knowledge_for_context(request.tenant_context),
                filters,
                organization_id=self._org(request).id,
            ),
            request.query_params,
            default_size=KNOWLEDGE_PAGE_SIZE,
        )
        # Автор последней правки нужен в списке: он стоит под датой в колонке
        # «Обновлено» (кадр KB1). Один запрос на всю страницу, не N+1.
        editors = knowledge_editors(
            organization_id=self._org(request).id,
            knowledge_ids=[item.id for item in page.items],
        )

        def payload(item):
            data = knowledge_payload(item, include_content=False)
            editor = editors.get(item.id)
            if editor:
                data["updatedBy"] = editor
            return data

        return Response(page_payload(page, payload))

    def post(self, request: Request) -> Response:
        try:
            data = knowledge_input(request.data)
            require_knowledge_create(context=request.tenant_context)
            knowledge = create_knowledge(
                context=request.tenant_context,
                data=data,
            )
        except ValidationError as error:
            return _validation_error(error)
        knowledge = self._write_knowledge(request, knowledge.id)
        self._audit(request, "created", knowledge)
        return Response({"knowledge": knowledge_payload(knowledge)}, status=201)


class KnowledgeDetailView(_KnowledgeBaseView):
    def get(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._read_knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        payload = knowledge_payload(knowledge)
        created_event = (
            AuditEvent.objects.filter(
                organization_id=knowledge.organization_id,
                action="ai.knowledge_created",
                object_type="Knowledge",
                object_id=str(knowledge.id),
            )
            .select_related("actor")
            .order_by("created_at")
            .first()
        )
        if created_event and created_event.actor:
            payload["createdBy"] = created_event.actor.full_name or created_event.actor.email
        editor = knowledge_editors(
            organization_id=knowledge.organization_id,
            knowledge_ids=[knowledge.id],
        ).get(knowledge.id)
        if editor:
            payload["updatedBy"] = editor
        # К каким агентам знание прикреплено — считает сервер: карточке больше
        # не нужен весь список агентов организации, чтобы это выяснить.
        payload["agents"] = [
            {
                "id": agent.id,
                "name": agent.channel.name,
                "groupName": agent.channel.group.name if agent.channel.group_id else None,
                "aiStatus": agent.status,
            }
            for agent in knowledge.agents.select_related("channel", "channel__group").order_by(
                "channel__name"
            )
        ]
        return Response({"knowledge": payload})

    def patch(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._write_knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        try:
            data = knowledge_input(request.data, current=knowledge)
            if not employee_can_write_knowledge(
                context=request.tenant_context,
                knowledge=knowledge,
            ):
                raise PermissionDenied("Knowledge is not manageable")
            knowledge = update_knowledge(
                context=request.tenant_context,
                knowledge=knowledge,
                data=data,
            )
        except ValidationError as error:
            return _validation_error(error)
        knowledge = self._write_knowledge(request, knowledge_id)
        self._audit(request, "updated", knowledge)
        return Response({"knowledge": knowledge_payload(knowledge)})

    def delete(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._write_knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        self._audit(request, "deleted", knowledge)
        delete_knowledge(context=request.tenant_context, knowledge=knowledge)
        return Response(status=204)


class KnowledgeImportView(_KnowledgeBaseView):
    def post(self, request: Request) -> Response:
        documents = request.data.get("documents")
        if not isinstance(documents, list) or not documents:
            return Response({"detail": "documents must be a non-empty list"}, status=400)
        result = import_knowledge_documents(
            context=request.tenant_context,
            documents=documents,
        )
        payload = result.payload()
        record_audit_event(
            action="ai.knowledge_imported",
            actor=request.user,
            organization=self._org(request),
            object_type="Knowledge",
            object_id="",
            payload=payload,
            request=request,
        )
        return Response(payload, status=201)


class KnowledgeReindexView(_KnowledgeBaseView):
    """Пересборка фрагментов знания по требованию (дизайн-базлайн v2, кадры
    KB1/KB4). Обычно индекс перестраивается при сохранении; кнопка нужна, когда
    агент отвечает старым текстом после сбоя или правки вложения."""

    def post(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._write_knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        reindex_knowledge(knowledge)
        self._audit(request, "reindexed", knowledge)
        knowledge = self._write_knowledge(request, knowledge_id)
        return Response({"knowledge": knowledge_payload(knowledge)})


class KnowledgeAttachmentUploadView(_KnowledgeBaseView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request, knowledge_id: int) -> Response:
        try:
            knowledge = self._write_knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "file is required (multipart/form-data)"}, status=400)
        try:
            attachment = add_attachment(
                context=request.tenant_context, knowledge=knowledge, upload=upload
            )
        except ValidationError as error:
            return _validation_error(error)
        self._audit(request, "attachment_added", knowledge)
        return Response({"attachment": attachment_payload(attachment)}, status=201)


class KnowledgeAttachmentDeleteView(_KnowledgeBaseView):
    def delete(self, request: Request, knowledge_id: int, attachment_id: int) -> Response:
        try:
            knowledge = self._write_knowledge(request, knowledge_id)
        except Knowledge.DoesNotExist:
            return Response({"detail": "Knowledge not found"}, status=404)
        attachment = knowledge.attachments.filter(id=attachment_id).first()
        if attachment is None:
            return Response({"detail": "Attachment not found"}, status=404)
        delete_attachment(context=request.tenant_context, attachment=attachment)
        self._audit(request, "attachment_deleted", knowledge)
        return Response(status=204)
