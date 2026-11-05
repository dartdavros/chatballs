"""Reply template CRUD; scope is resolved from the authenticated membership."""

from django.db import transaction

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.template_access import (
    creation_owner,
    library_object,
    require_library_management,
    validate_unchanged_scope,
)
from chatballs.conversations.template_models import ReplyTemplate, ReplyTemplateTagLink
from chatballs.conversations.template_search import SEARCH_PARAMS, search_templates
from chatballs.conversations.template_validation import (
    library_name,
    save_named,
    template_relations,
    template_text,
)


def template_payload(template):
    return {
        "id": template.pk, "title": template.title, "text": template.text,
        "updatedAt": template.updated_at.isoformat(), "scope": template.scope,
        "ownerId": template.owner_id, "categoryId": template.category_id,
        "tagIds": [tag.pk for tag in template.tags.all()],
    }

def save_template(template, data, context):
    validate_unchanged_scope(template, data)
    if "title" in data or not template.pk:
        template.title = library_name(data.get("title"))
    if "text" in data or not template.pk:
        template.text = template_text(data.get("text"), context)
    tags = template_relations(template, data)
    with transaction.atomic():
        save_named(template, "title")
        if tags is not None:
            ReplyTemplateTagLink.objects.filter(template=template).delete()
            ReplyTemplateTagLink.objects.bulk_create([
                ReplyTemplateTagLink(organization_id=template.organization_id, template=template, tag=tag)
                for tag in tags
            ])


def list_templates(context, params):
    templates = search_templates(context.membership, params)
    if SEARCH_PARAMS.intersection(params):
        return page_payload(paginate(templates, params), template_payload)
    return {"items": [template_payload(item) for item in templates]}


def get_template(context, template_id):
    return {"template": template_payload(library_object(ReplyTemplate, context.membership, template_id))}


def create_template(context, data):
    actor = context.membership
    template = ReplyTemplate(organization_id=actor.organization_id, owner_id=creation_owner(actor, data))
    save_template(template, data, context)
    return {"template": template_payload(template)}


@transaction.atomic
def update_template(context, template_id, data):
    actor = context.membership
    template = library_object(ReplyTemplate, actor, template_id)
    template = ReplyTemplate.objects.select_for_update().get(pk=template.pk)
    require_library_management(actor, template.owner_id)
    save_template(template, data, context)
    return {"template": template_payload(template)}


def delete_template(context, template_id):
    template = library_object(ReplyTemplate, context.membership, template_id)
    require_library_management(context.membership, template.owner_id)
    template.delete()
