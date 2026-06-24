from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai import documents as doc_service
from hub_platform.ai.models import (
    InclusionMode,
    KnowledgeCategory,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    PromptCategory,
    PromptDocument,
    PromptDocumentVersion,
)
from hub_platform.ai.selectors import document_for_organization, documents_for_organization
from hub_platform.ai.serializers import knowledge_payload, prompt_payload
from hub_platform.api.permissions import IsOwner
from hub_platform.identity.audit import record_audit_event
from hub_platform.products.models import Product


class _DocConfig(APIView):
    permission_classes = [IsOwner]
    document_model = None
    version_model = None
    payload = staticmethod(lambda document: {})
    valid_categories: set = set()
    supports_inclusion = False
    audit_prefix = "ai.document"

    def _org(self, request: Request):
        return request.user.employee_profile.organization

    def _document(self, request: Request, document_id: int):
        return document_for_organization(
            self.document_model, organization_id=self._org(request).id, document_id=document_id
        )

    def _audit(self, request: Request, action: str, document) -> None:
        record_audit_event(
            action=f"{self.audit_prefix}_{action}",
            actor=request.user,
            organization=self._org(request),
            object_type=self.document_model.__name__,
            object_id=str(document.id),
            request=request,
        )

    def after_publish(self, version) -> None:
        # Хук для типоспецифичного действия после публикации версии.
        pass


class DocumentListCreateView(_DocConfig):
    def get(self, request: Request) -> Response:
        documents = documents_for_organization(
            self.document_model, self._org(request).id, request.query_params.get("product")
        )
        return Response({"items": [self.payload(document) for document in documents]})

    def post(self, request: Request) -> Response:
        body = request.data
        org = self._org(request)
        try:
            product = Product.objects.get(organization=org, code=str(body.get("product", "")))
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=400)

        code = str(body.get("code", "")).strip()
        title = str(body.get("title", "")).strip()
        category = str(body.get("category", ""))
        if not code or not title:
            return Response({"detail": "Code and title are required"}, status=400)
        if category not in self.valid_categories:
            return Response({"detail": "Unknown category"}, status=400)
        if self.document_model.objects.filter(product=product, code=code).exists():
            return Response({"detail": "Document code already exists"}, status=400)

        fields = {"product": product, "code": code, "title": title, "category": category}
        if self.supports_inclusion:
            inclusion = str(body.get("inclusionMode", InclusionMode.RETRIEVAL))
            if inclusion not in InclusionMode.values:
                return Response({"detail": "Unknown inclusion mode"}, status=400)
            fields["inclusion_mode"] = inclusion

        document = doc_service.create_document(
            document_model=self.document_model,
            version_model=self.version_model,
            content=str(body.get("content", "")),
            author=request.user,
            **fields,
        )
        document = self._document(request, document.id)
        self._audit(request, "created", document)
        return Response({"document": self.payload(document)}, status=201)


class DocumentDetailView(_DocConfig):
    def get(self, request: Request, document_id: int) -> Response:
        try:
            document = self._document(request, document_id)
        except self.document_model.DoesNotExist:
            return Response({"detail": "Document not found"}, status=404)
        return Response({"document": self.payload(document)})


class DocumentAddVersionView(_DocConfig):
    def post(self, request: Request, document_id: int) -> Response:
        try:
            document = self._document(request, document_id)
        except self.document_model.DoesNotExist:
            return Response({"detail": "Document not found"}, status=404)
        doc_service.add_version(
            version_model=self.version_model,
            document=document,
            content=str(request.data.get("content", "")),
            author=request.user,
        )
        document = self._document(request, document_id)
        self._audit(request, "version_added", document)
        return Response({"document": self.payload(document)}, status=201)


class DocumentPublishVersionView(_DocConfig):
    def post(self, request: Request, document_id: int, version: int) -> Response:
        try:
            document = self._document(request, document_id)
        except self.document_model.DoesNotExist:
            return Response({"detail": "Document not found"}, status=404)
        try:
            target = self.version_model.objects.get(document=document, version=version)
        except self.version_model.DoesNotExist:
            return Response({"detail": "Version not found"}, status=404)
        doc_service.publish_version(version=target)
        self.after_publish(target)
        document = self._document(request, document_id)
        self._audit(request, "version_published", document)
        return Response({"document": self.payload(document)})


class DocumentRollbackView(_DocConfig):
    def post(self, request: Request, document_id: int) -> Response:
        try:
            document = self._document(request, document_id)
        except self.document_model.DoesNotExist:
            return Response({"detail": "Document not found"}, status=404)
        try:
            source = self.version_model.objects.get(document=document, version=int(request.data.get("version", 0)))
        except (self.version_model.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Version not found"}, status=404)
        doc_service.rollback_document(
            version_model=self.version_model, document=document, source_version=source, author=request.user
        )
        document = self._document(request, document_id)
        self._audit(request, "rolled_back", document)
        return Response({"document": self.payload(document)}, status=201)


class _DocumentStatusView(_DocConfig):
    target_enabled: bool

    def post(self, request: Request, document_id: int) -> Response:
        try:
            document = self._document(request, document_id)
        except self.document_model.DoesNotExist:
            return Response({"detail": "Document not found"}, status=404)
        document.is_enabled = self.target_enabled
        document.save(update_fields=["is_enabled", "updated_at"])
        self._audit(request, "enabled" if self.target_enabled else "disabled", document)
        return Response({"document": self.payload(document)})


class DocumentEnableView(_DocumentStatusView):
    target_enabled = True


class DocumentDisableView(_DocumentStatusView):
    target_enabled = False


# --- Knowledge / prompt concrete configs ---


class _KnowledgeConfig:
    document_model = KnowledgeDocument
    version_model = KnowledgeDocumentVersion
    payload = staticmethod(knowledge_payload)
    valid_categories = set(KnowledgeCategory.values)
    supports_inclusion = True
    audit_prefix = "ai.knowledge"

    def after_publish(self, version) -> None:
        from hub_platform.ai.indexing import reindex_knowledge_version

        reindex_knowledge_version(version)


class _PromptConfig:
    document_model = PromptDocument
    version_model = PromptDocumentVersion
    payload = staticmethod(prompt_payload)
    valid_categories = set(PromptCategory.values)
    supports_inclusion = False
    audit_prefix = "ai.prompt"


class KnowledgeListCreateView(_KnowledgeConfig, DocumentListCreateView): pass
class KnowledgeDetailView(_KnowledgeConfig, DocumentDetailView): pass
class KnowledgeAddVersionView(_KnowledgeConfig, DocumentAddVersionView): pass
class KnowledgePublishVersionView(_KnowledgeConfig, DocumentPublishVersionView): pass
class KnowledgeRollbackView(_KnowledgeConfig, DocumentRollbackView): pass
class KnowledgeEnableView(_KnowledgeConfig, DocumentEnableView): pass
class KnowledgeDisableView(_KnowledgeConfig, DocumentDisableView): pass

class PromptListCreateView(_PromptConfig, DocumentListCreateView): pass
class PromptDetailView(_PromptConfig, DocumentDetailView): pass
class PromptAddVersionView(_PromptConfig, DocumentAddVersionView): pass
class PromptPublishVersionView(_PromptConfig, DocumentPublishVersionView): pass
class PromptRollbackView(_PromptConfig, DocumentRollbackView): pass
class PromptEnableView(_PromptConfig, DocumentEnableView): pass
class PromptDisableView(_PromptConfig, DocumentDisableView): pass
