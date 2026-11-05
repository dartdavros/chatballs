"""Shared library grants retain administrator authority and audit."""

from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied

from chatballs.conversations.template_access import can_manage_shared
from chatballs.conversations.template_models import ReplyTemplateManagementGrant
from chatballs.conversations.template_validation import LibraryValidationError
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.policy import can_administer_access


def library_permissions(context):
    return {"canManageShared": can_manage_shared(context.membership),
        "canGrantSharedManagement": can_administer_access(context.membership)}


def grant_target(context, membership_id):
    if not can_administer_access(context.membership):
        raise PermissionDenied(t("conversations.template_management_denied"))
    try:
        return OrganizationMembership.objects.get(organization_id=context.organization_id, pk=membership_id)
    except OrganizationMembership.DoesNotExist:
        raise NotFound(t("admin.employee_not_found")) from None


def management_grant(context, membership_id):
    target = grant_target(context, membership_id)
    return {"membershipId": target.pk, "canManageShared": can_manage_shared(target),
        "granted": ReplyTemplateManagementGrant.objects.filter(membership=target).exists()}


@transaction.atomic
def set_management_grant(context, membership_id, data, *, request=None):
    target = grant_target(context, membership_id)
    granted = data.get("granted")
    if type(granted) is not bool or set(data) != {"granted"}:
        raise LibraryValidationError(t("conversations.template_grant_invalid"))
    if granted:
        ReplyTemplateManagementGrant.objects.get_or_create(organization_id=target.organization_id, membership=target)
    else:
        ReplyTemplateManagementGrant.objects.filter(membership=target).delete()
    record_audit_event(action="conversations.template_management_changed", actor=context.actor_user,
        organization=context.organization, object_type="OrganizationMembership", object_id=str(target.pk),
        payload={"granted": granted}, request=request)
    return {"membershipId": target.pk, "granted": granted, "canManageShared": can_manage_shared(target)}
