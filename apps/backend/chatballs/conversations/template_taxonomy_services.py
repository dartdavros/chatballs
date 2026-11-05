"""Shared operations for the two fixed product taxonomies."""

from chatballs.conversations.template_access import (
    creation_owner,
    library_object,
    require_library_management,
    validate_unchanged_scope,
    visible_library,
)
from chatballs.conversations.template_validation import library_name, save_named


def taxonomy_payload(item):
    return {"id": item.pk, "name": item.name, "scope": item.scope, "ownerId": item.owner_id}


def list_taxonomy(model, context):
    return {"items": [taxonomy_payload(row) for row in visible_library(model, context.membership)]}


def get_taxonomy(model, context, item_id):
    return {"item": taxonomy_payload(library_object(model, context.membership, item_id))}


def create_taxonomy(model, context, data):
    actor = context.membership
    item = model(organization_id=actor.organization_id, owner_id=creation_owner(actor, data),
        name=library_name(data.get("name")))
    validate_unchanged_scope(item, data)
    save_named(item, "name")
    return {"item": taxonomy_payload(item)}


def update_taxonomy(model, context, item_id, data):
    actor = context.membership
    item = library_object(model, actor, item_id)
    require_library_management(actor, item.owner_id)
    validate_unchanged_scope(item, data)
    item.name = library_name(data.get("name", item.name))
    save_named(item, "name")
    return {"item": taxonomy_payload(item)}


def delete_taxonomy(model, context, item_id):
    item = library_object(model, context.membership, item_id)
    require_library_management(context.membership, item.owner_id)
    item.delete()
