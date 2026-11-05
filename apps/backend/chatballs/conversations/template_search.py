"""Search only within libraries visible to the current membership."""

from django.db.models import Count, Q
from rest_framework.exceptions import NotFound

from chatballs.conversations.template_access import library_object, visible_library
from chatballs.conversations.template_models import (
    ReplyTemplate,
    ReplyTemplateCategory,
    ReplyTemplateTag,
    ReplyTemplateTagLink,
)
from chatballs.conversations.template_validation import LibraryValidationError
from chatballs.i18n import t

SEARCH_PARAMS = frozenset({"q", "scope", "categoryId", "tagIds", "page", "pageSize"})


def filter_id(raw):
    try:
        value = int(raw)
    except (ValueError, TypeError):
        raise LibraryValidationError(t("conversations.template_relation_invalid")) from None
    if not 0 < value <= 2**63 - 1:
        raise LibraryValidationError(t("conversations.template_relation_invalid"))
    return value


def search_templates(actor, params):
    templates = visible_library(ReplyTemplate, actor)
    if "scope" in params:
        scope = params["scope"]
        if scope not in ("SHARED", "PERSONAL"):
            raise LibraryValidationError(t("conversations.template_scope_invalid"))
        templates = templates.filter(owner_id=None if scope == "SHARED" else actor.pk)

    query = params.get("q", "").strip()
    if query:
        templates = templates.filter(Q(title__icontains=query) | Q(text__icontains=query))

    if "categoryId" in params:
        category = library_object(ReplyTemplateCategory, actor, filter_id(params["categoryId"]))
        templates = templates.filter(category_id=category.pk)

    groups = params.getlist("tagIds") if hasattr(params, "getlist") else [str(pk) for pk in params.get("tagIds", [])]
    tag_ids = {
        filter_id(raw)
        for group in groups
        for raw in group.split(",")
    }
    if tag_ids:
        if visible_library(ReplyTemplateTag, actor).filter(pk__in=tag_ids).count() != len(tag_ids):
            raise NotFound(t("conversations.template_not_found"))
        # One grouped subquery matches all tags without duplicating templates.
        matching = ReplyTemplateTagLink.objects.filter(
            organization_id=actor.organization_id, tag_id__in=tag_ids,
        ).values("template_id").annotate(tag_count=Count("tag_id")).filter(tag_count=len(tag_ids))
        templates = templates.filter(pk__in=matching.values("template_id"))

    return templates.order_by("title", "id").prefetch_related("tags")
