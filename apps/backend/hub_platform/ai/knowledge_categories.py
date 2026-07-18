from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.ai.knowledge_types import UNCATEGORIZED_CATEGORY_NAME
from hub_platform.ai.models import KnowledgeCategory
from hub_platform.identity.models import Organization
from hub_platform.tenancy.context import TenantContext


def ensure_uncategorized_category(organization: Organization) -> KnowledgeCategory:
    category, _ = KnowledgeCategory.objects.get_or_create(
        organization=organization,
        is_system=True,
        defaults={
            "name": UNCATEGORIZED_CATEGORY_NAME,
            "parent": None,
            "sort_order": 0,
        },
    )
    return category


def _validate_category_context(
    *, context: TenantContext, category: KnowledgeCategory
) -> None:
    if category.organization_id != context.organization_id:
        raise ValidationError({"category": "Category belongs to another organization"})


def _validate_parent(
    *, context: TenantContext, parent: KnowledgeCategory | None
) -> None:
    if parent is not None and parent.organization_id != context.organization_id:
        raise ValidationError({"parent": "Parent category belongs to another organization"})


@transaction.atomic
def create_category(
    *,
    context: TenantContext,
    name: str,
    parent: KnowledgeCategory | None = None,
    sort_order: int = 0,
) -> KnowledgeCategory:
    _validate_parent(context=context, parent=parent)
    return KnowledgeCategory.objects.create(
        organization=context.organization,
        parent=parent,
        name=name,
        sort_order=sort_order,
    )


@transaction.atomic
def rename_category(
    *, context: TenantContext, category: KnowledgeCategory, name: str
) -> KnowledgeCategory:
    _validate_category_context(context=context, category=category)
    if category.is_system:
        raise ValidationError({"category": "System category is immutable"})
    locked = KnowledgeCategory.objects.select_for_update().get(pk=category.pk)
    locked.name = name
    locked.save(update_fields=["name"])
    return locked


@transaction.atomic
def move_category(
    *,
    context: TenantContext,
    category: KnowledgeCategory,
    parent: KnowledgeCategory | None,
    sort_order: int | None = None,
) -> KnowledgeCategory:
    _validate_category_context(context=context, category=category)
    _validate_parent(context=context, parent=parent)
    if category.is_system:
        raise ValidationError({"category": "System category is immutable"})
    locked_categories = {
        item.pk: item
        for item in KnowledgeCategory.objects.select_for_update().filter(
            organization_id=context.organization_id
        )
    }
    locked = locked_categories[category.pk]
    locked.parent = locked_categories[parent.pk] if parent is not None else None
    update_fields = ["parent"]
    if sort_order is not None:
        locked.sort_order = sort_order
        update_fields.append("sort_order")
    locked.save(update_fields=update_fields)
    return locked


@transaction.atomic
def update_category(
    *,
    context: TenantContext,
    category: KnowledgeCategory,
    name: str,
    parent: KnowledgeCategory | None,
    sort_order: int,
) -> KnowledgeCategory:
    _validate_category_context(context=context, category=category)
    _validate_parent(context=context, parent=parent)
    if category.is_system:
        raise ValidationError({"category": "System category is immutable"})
    locked_categories = {
        item.pk: item
        for item in KnowledgeCategory.objects.select_for_update().filter(
            organization_id=context.organization_id
        )
    }
    locked = locked_categories[category.pk]
    locked.name = name
    locked.parent = locked_categories[parent.pk] if parent is not None else None
    locked.sort_order = sort_order
    locked.save(update_fields=["name", "parent", "sort_order"])
    return locked


@transaction.atomic
def delete_category(*, context: TenantContext, category: KnowledgeCategory) -> None:
    _validate_category_context(context=context, category=category)
    locked = KnowledgeCategory.objects.select_for_update().get(pk=category.pk)
    locked.delete()
