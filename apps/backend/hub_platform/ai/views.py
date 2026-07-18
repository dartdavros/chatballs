from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai.models import Knowledge
from hub_platform.ai.knowledge_policy import require_knowledge_create
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.selectors import (
    KnowledgeFilters,
    apply_knowledge_filters,
    knowledge_for_context,
    knowledge_item_for_context,
    writable_knowledge_for_employee,
    writable_knowledge_item_for_employee,
)
from hub_platform.ai.serializers import attachment_payload, knowledge_payload
from hub_platform.ai.services import (
    KnowledgeInput,
    add_attachment,
    create_knowledge,
    delete_attachment,
    delete_knowledge,
    update_knowledge,
)
from hub_platform.api.permissions import HasCapability, HasEntitlement
from hub_platform.identity.audit import record_audit_event


def _validation_error(error: ValidationError) -> Response:
    detail = "; ".join(message for messages in error.message_dict.values() for message in messages) if hasattr(error, "message_dict") else "; ".join(error.messages)
    return Response({"detail": detail}, status=400)


# --- Знания (ADR-HUB-0023) ---


def _knowledge_input(body: dict[str, object], *, current: Knowledge | None = None) -> KnowledgeInput:
    is_enabled = body.get("isEnabled", current.is_enabled if current else True)
    return KnowledgeInput(
        title=str(body.get("title", current.title if current else "")),
        description=str(body.get("description", current.description if current else "")),
        content=str(body.get("content", current.content if current else "")),
        is_enabled=bool(is_enabled),
    )


def _optional_id(value: str | None, field: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({field: "Integer id required"}) from error
    if parsed <= 0:
        raise ValidationError({field: "Positive integer id required"})
    return parsed


def _knowledge_filters(request: Request) -> KnowledgeFilters:
    visibility = request.query_params.get("visibility") or None
    if visibility is not None and visibility not in KnowledgeVisibility.values:
        raise ValidationError({"visibility": "Unknown knowledge visibility"})
    raw_enabled = request.query_params.get("isEnabled")
    if raw_enabled in (None, ""):
        is_enabled = None
    elif raw_enabled.lower() == "true":
        is_enabled = True
    elif raw_enabled.lower() == "false":
        is_enabled = False
    else:
        raise ValidationError({"isEnabled": "Boolean required"})
    return KnowledgeFilters(
        category_id=_optional_id(request.query_params.get("category"), "category"),
        department_id=_optional_id(
            request.query_params.get("department"), "department"
        ),
        visibility=visibility,
        is_enabled=is_enabled,
        search=request.query_params.get("search", ""),
    )


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
            filters = _knowledge_filters(request)
        except ValidationError as error:
            return _validation_error(error)
        items = apply_knowledge_filters(
            knowledge_for_context(request.tenant_context), filters
        )
        return Response({"items": [knowledge_payload(item, include_content=False) for item in items]})

    def post(self, request: Request) -> Response:
        try:
            require_knowledge_create(
                context=request.tenant_context,
                visibility=KnowledgeVisibility.ORGANIZATION,
                department_ids=[],
            )
            knowledge = create_knowledge(
                context=request.tenant_context,
                data=_knowledge_input(request.data),
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
            knowledge = update_knowledge(
                context=request.tenant_context,
                knowledge=knowledge,
                data=_knowledge_input(request.data, current=knowledge),
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
