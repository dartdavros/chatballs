"""Contact card operations shared by product HTTP and scenario actions."""

from rest_framework.exceptions import PermissionDenied, ValidationError

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.clients import client_detail, client_row, clients_queryset
from chatballs.conversations.contact_card import save_card_fields
from chatballs.conversations.contacts_merge import merge_contacts, revert_merge
from chatballs.conversations.models import Contact
from chatballs.conversations.selectors import visible_conversations_for
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import EmployeeRole
from chatballs.identity.policy import ResourceScope, authorize


def _require(context, capability):
    if not authorize(context.membership, capability, ResourceScope(context.organization_id)):
        raise PermissionDenied(t("conversations.not_found"))


def contacts(context, params):
    _require(context, "customers.view")
    return page_payload(paginate(clients_queryset(context.organization_id, params, context=context), params), client_row)


def card(context, contact_id):
    _require(context, "customers.view")
    return {"client": client_detail(context.organization_id, contact_id, context=context)}


def change_card(context, contact_id, data, *, request=None):
    _require(context, "customers.manage")
    contact = Contact.objects.get(pk=contact_id, organization_id=context.organization_id)
    changed, error = save_card_fields(contact, data)
    if error:
        raise ValidationError({"detail": error})
    if changed:
        record_audit_event(action="conversation.contact_updated", actor=context.actor_user,
            organization=context.organization, object_type="Contact", object_id=str(contact.pk),
            payload={"fields": changed}, request=request)
    return {"client": client_detail(context.organization_id, contact_id)}


def _owner(context):
    _require(context, "customers.manage")
    if context.membership is None or context.membership.role != EmployeeRole.OWNER:
        raise PermissionDenied({"detail": t("sales.merge_owner_only")})


def merge(context, contact_id, source_id, reason, *, request=None):
    _owner(context)
    merge_contacts(organization=context.organization, target_id=contact_id, source_id=source_id,
        reason=reason, actor=context.actor_user, request=request)
    return {"client": client_detail(context.organization_id, contact_id)}


def unmerge(context, contact_id, merge_id, reason, *, request=None):
    _owner(context)
    revert_merge(organization=context.organization, merge_id=merge_id, reason=reason,
        actor=context.actor_user, request=request)
    return {"client": client_detail(context.organization_id, contact_id)}


def avatar(context, contact_id):
    _require(context, "conversations.view")
    contact = Contact.objects.filter(pk=contact_id, organization_id=context.organization_id).first()
    if contact is None or not contact.avatar or not visible_conversations_for(context).filter(contact_id=contact_id).exists():
        raise Contact.DoesNotExist
    return contact
