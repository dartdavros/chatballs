from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai.api_errors import validation_error_response
from chatballs.ai.knowledge_categories import (
    create_category,
    delete_category,
    update_category,
)
from chatballs.ai.knowledge_policy import require_category_manage
from chatballs.ai.models import KnowledgeCategory
from chatballs.ai.selectors import category_tree_for_employee
from chatballs.ai.serializers import category_payload
from chatballs.api.permissions import HasCapability
from chatballs.identity.audit import record_audit_event


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise ValidationError({field: "Integer required"})
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({field: "Integer required"}) from error


def _category(request: Request, category_id: int) -> KnowledgeCategory:
    return KnowledgeCategory.objects.select_related("parent").get(
        organization_id=request.tenant_context.organization_id,
        id=category_id,
    )


def _parent(
    request: Request, value: object, *, field_present: bool
) -> KnowledgeCategory | None:
    if not field_present or value is None:
        return None
    parent_id = _integer(value, "parentId")
    try:
        return _category(request, parent_id)
    except KnowledgeCategory.DoesNotExist as error:
        raise ValidationError({"parentId": "Parent category not found"}) from error


def _audit(
    request: Request,
    action: str,
    category: KnowledgeCategory,
    *,
    object_id: int | None = None,
) -> None:
    record_audit_event(
        action=f"ai.knowledge_category_{action}",
        actor=request.user,
        organization=request.tenant_context.organization,
        object_type="KnowledgeCategory",
        object_id=str(object_id if object_id is not None else category.id),
        request=request,
    )


def _category_payload(request: Request, category_id: int) -> dict[str, object]:
    category = next(
        item
        for item in category_tree_for_employee(context=request.tenant_context)
        if item.id == category_id
    )
    return category_payload(category)


class KnowledgeCategoryListCreateView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "ai.view", "POST": "ai.manage"}

    def get(self, request: Request) -> Response:
        categories = category_tree_for_employee(context=request.tenant_context)
        return Response({"items": [category_payload(item) for item in categories]})

    def post(self, request: Request) -> Response:
        try:
            require_category_manage(context=request.tenant_context)
            parent = _parent(
                request,
                request.data.get("parentId"),
                field_present="parentId" in request.data,
            )
            category = create_category(
                context=request.tenant_context,
                name=str(request.data.get("name", "")),
                parent=parent,
                sort_order=_integer(request.data.get("sortOrder", 0), "sortOrder"),
            )
        except ValidationError as error:
            return validation_error_response(error)
        _audit(request, "created", category)
        return Response(
            {"category": _category_payload(request, category.id)}, status=201
        )


class KnowledgeCategoryDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "ai.manage"

    def patch(self, request: Request, category_id: int) -> Response:
        try:
            require_category_manage(context=request.tenant_context)
            category = _category(request, category_id)
        except KnowledgeCategory.DoesNotExist:
            return Response({"detail": "Category not found"}, status=404)
        try:
            parent = (
                _parent(request, request.data.get("parentId"), field_present=True)
                if "parentId" in request.data
                else category.parent
            )
            updated = update_category(
                context=request.tenant_context,
                category=category,
                name=str(request.data.get("name", category.name)),
                parent=parent,
                sort_order=_integer(
                    request.data.get("sortOrder", category.sort_order), "sortOrder"
                ),
            )
        except ValidationError as error:
            return validation_error_response(error)
        _audit(request, "updated", updated)
        return Response({"category": _category_payload(request, updated.id)})

    def delete(self, request: Request, category_id: int) -> Response:
        try:
            require_category_manage(context=request.tenant_context)
            category = _category(request, category_id)
        except KnowledgeCategory.DoesNotExist:
            return Response({"detail": "Category not found"}, status=404)
        try:
            deleted_id = category.id
            delete_category(context=request.tenant_context, category=category)
        except ValidationError as error:
            return validation_error_response(error)
        _audit(request, "deleted", category, object_id=deleted_id)
        return Response(status=204)
