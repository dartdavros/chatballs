from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.api_errors import validation_error_response
from hub_platform.ai.knowledge_api_inputs import knowledge_filters, knowledge_input
from hub_platform.ai.knowledge_policy import (
    employee_can_write_knowledge,
    require_knowledge_create,
)
from hub_platform.ai.knowledge_services import (
    KnowledgeInput,
    add_attachment,
    create_knowledge,
    delete_attachment,
    delete_knowledge,
    update_knowledge,
)
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.models import Knowledge
from hub_platform.ai.selectors import (
    apply_knowledge_filters,
    knowledge_for_context,
    knowledge_item_for_context,
    writable_knowledge_for_employee,
    writable_knowledge_item_for_employee,
)
from hub_platform.ai.serializers import attachment_payload, knowledge_payload
from hub_platform.api.permissions import HasCapability, HasEntitlement
from hub_platform.identity.audit import record_audit_event


_validation_error = validation_error_response


class _KnowledgeBaseView(APIView):
    permission_classes = [HasEntitlement, HasCapability]
    required_entitlement = "knowledge_base"
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
        items = apply_knowledge_filters(
            knowledge_for_context(request.tenant_context), filters
        )
        return Response({"items": [knowledge_payload(item, include_content=False) for item in items]})

    def post(self, request: Request) -> Response:
        try:
            data = knowledge_input(request.data)
            require_knowledge_create(
                context=request.tenant_context,
                visibility=data.visibility or KnowledgeVisibility.ORGANIZATION,
                department_ids=data.department_ids or (),
            )
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
        return Response({"knowledge": knowledge_payload(knowledge)})

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
                visibility=data.visibility,
                department_ids=data.department_ids,
            ):
                raise PermissionDenied("Knowledge scope is not manageable")
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
            knowledge = writable_knowledge_for_employee(
                context=request.tenant_context
            ).filter(title=title).first()
            if knowledge is None:
                try:
                    require_knowledge_create(
                        context=request.tenant_context,
                        visibility=KnowledgeVisibility.ORGANIZATION,
                        department_ids=[],
                    )
                    create_knowledge(
                        context=request.tenant_context,
                        data=KnowledgeInput(title=title, description=description, content=content, is_enabled=True),
                    )
                    created += 1
                except PermissionDenied:
                    failed.append(
                        {"title": title, "detail": "Knowledge is not manageable"}
                    )
            elif knowledge.content == content and knowledge.description == (description or knowledge.description):
                unchanged += 1
            else:
                update_knowledge(
                    context=request.tenant_context,
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
