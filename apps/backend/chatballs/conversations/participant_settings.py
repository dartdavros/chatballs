"""Organization participant limits, with the original policy and audit."""

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from chatballs.conversations.participant_inputs import LimitInput
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import AuditEvent, Organization
from chatballs.identity.policy import ResourceScope, authorize


def _payload(organization, saved):
    return {"additionalParticipantLimit": organization.additional_participant_limit,
        "updatedAt": saved.created_at.isoformat() if saved else None,
        "updatedBy": (saved.actor.full_name or saved.actor.email) if saved and saved.actor else ""}


@transaction.atomic
def participant_limit(context, changes=None, *, request=None):
    capability = "conversations.view" if changes is None else "settings.manage"
    if not authorize(context.membership, capability, ResourceScope(context.organization_id)):
        raise PermissionDenied()
    # Keep the API validation order and the same lock as composition changes.
    clean = None
    if changes is not None:
        serializer = LimitInput(data=changes)
        serializer.is_valid(raise_exception=True)
        clean = serializer.validated_data
    organization = Organization.objects.select_for_update().get(pk=context.organization_id)
    if clean is None:
        saved = AuditEvent.objects.filter(organization_id=organization.pk,
            action="conversations.participant_limit_changed").select_related("actor").order_by("-created_at", "-pk").first()
    else:
        organization.additional_participant_limit = clean["additionalParticipantLimit"]
        organization.save(update_fields=["additional_participant_limit"])
        saved = record_audit_event(action="conversations.participant_limit_changed",
            organization=organization, actor=context.actor_user, object_type="Organization",
            object_id=str(organization.pk), request=request,
            payload={"additionalParticipantLimit": organization.additional_participant_limit})
    return _payload(organization, saved)
