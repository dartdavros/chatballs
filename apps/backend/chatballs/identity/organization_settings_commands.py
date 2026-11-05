"""Organization settings and logo commands, including their original audit."""

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied

from chatballs.i18n import t
from chatballs.identity.administration_payloads import (
    administration_languages,
    administration_timezones,
    organization_settings_payload,
)
from chatballs.identity.administration_services import (
    OrganizationSettingsInput,
    delete_organization_logo,
    replace_organization_logo,
    update_organization_settings,
)
from chatballs.identity.audit import record_audit_event
from chatballs.identity.policy import has_capability_any_scope


def _require(context, capability):
    if not has_capability_any_scope(context.membership, capability):
        raise PermissionDenied()


def read_settings(context):
    _require(context, "settings.view")
    return {"organization": organization_settings_payload(context.organization),
        "timezones": administration_timezones(), "languages": administration_languages()}


def _audit(context, organization, action, request):
    record_audit_event(action=f"administration.{action}", actor=context.actor_user,
        organization=organization, object_type="Organization", object_id=str(organization.public_id),
        request=request)
    return {"organization": organization_settings_payload(organization)}


@transaction.atomic
def update_settings(context, body, *, request=None):
    _require(context, "settings.manage")
    organization = context.organization
    if "operationMode" in body and body["operationMode"] is None:
        raise ValidationError(t("admin.operation_mode_invalid"))
    organization = update_organization_settings(context=context, data=OrganizationSettingsInput(
        name=str(body.get("name", organization.name)), timezone=str(body.get("timezone", organization.timezone)),
        language=str(body.get("language", organization.language)), operation_mode=body.get("operationMode")))
    return _audit(context, organization, "organization_updated", request)


def read_logo(context):
    organization = context.organization
    if not organization.logo:
        raise NotFound(t("admin.logo_not_uploaded"))
    return organization.logo, organization.logo_content_type or "application/octet-stream"


@transaction.atomic
def upload_logo(context, upload, *, request=None):
    _require(context, "settings.manage")
    if upload is None:
        raise ValidationError(t("admin.choose_logo_file"))
    organization = replace_organization_logo(context=context, upload=upload)
    return _audit(context, organization, "logo_updated", request)


@transaction.atomic
def remove_logo(context, *, request=None):
    _require(context, "settings.manage")
    organization = delete_organization_logo(context=context)
    return _audit(context, organization, "logo_deleted", request)
