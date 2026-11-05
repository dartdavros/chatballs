"""Category application commands shared by HTTP and scenario adapters."""

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied

from chatballs.ai import knowledge_categories as domain
from chatballs.ai.knowledge_policy import require_category_manage
from chatballs.ai.models import KnowledgeCategory
from chatballs.ai.selectors import category_tree_for_employee
from chatballs.ai.serializers import category_payload
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.policy import ResourceScope, authorize


def integer(value, field):
    if isinstance(value, bool):
        raise ValidationError({field: t("api.integer_required")})
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({field: t("api.integer_required")}) from error


def _category(context, category_id):
    return KnowledgeCategory.objects.select_related("parent").get(
        organization_id=context.organization_id, pk=category_id)


def _parent(context, value):
    if value is None:
        return None
    try:
        return _category(context, integer(value, "parentId"))
    except KnowledgeCategory.DoesNotExist as error:
        raise ValidationError({"parentId": t("ai.parent_category_not_found")}) from error


def _managed(context, category_id):
    require_category_manage(context=context)
    try:
        return _category(context, category_id)
    except KnowledgeCategory.DoesNotExist:
        raise NotFound(t("ai.category_not_found")) from None


def _audit(context, action, category_id, request):
    record_audit_event(action=f"ai.knowledge_category_{action}", actor=context.actor_user,
        organization=context.organization, object_type="KnowledgeCategory",
        object_id=str(category_id), request=request)


def _payload(context, category_id):
    return category_payload(next(item for item in category_tree_for_employee(context=context)
        if item.id == category_id))


def list_categories(context):
    if not authorize(context.membership, "ai.view", ResourceScope(context.organization_id)):
        raise PermissionDenied()
    return {"items": [category_payload(item) for item in category_tree_for_employee(context=context)]}


@transaction.atomic
def create_category(context, data, *, request=None):
    require_category_manage(context=context)
    category = domain.create_category(context=context, name=str(data.get("name", "")),
        parent=_parent(context, data.get("parentId")), sort_order=integer(data.get("sortOrder", 0), "sortOrder"))
    _audit(context, "created", category.id, request)
    return {"category": _payload(context, category.id)}


@transaction.atomic
def update_category(context, category_id, data, *, request=None):
    category = _managed(context, category_id)
    updated = domain.update_category(context=context, category=category,
        name=str(data.get("name", category.name)),
        parent=_parent(context, data.get("parentId")) if "parentId" in data else category.parent,
        sort_order=integer(data.get("sortOrder", category.sort_order), "sortOrder"))
    _audit(context, "updated", updated.id, request)
    return {"category": _payload(context, updated.id)}


@transaction.atomic
def delete_category(context, category_id, *, request=None):
    category = _managed(context, category_id)
    domain.delete_category(context=context, category=category)
    _audit(context, "deleted", category_id, request)
