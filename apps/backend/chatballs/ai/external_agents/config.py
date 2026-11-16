"""Organization opt-in and explicit new connection setup; networking outside transactions."""

import secrets

from django.core.exceptions import ValidationError

from chatballs.ai.external_agents.adapter import (
    ADAPTER,
    clean_address,
)
from chatballs.ai.external_agents.config_access import (
    connection_for,
    connection_payload,
    owner,
)
from chatballs.ai.external_agents.config_models import ExternalAgentConnection
from chatballs.ai.external_agents.config_policy import invalid
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.integrations.service_connections.binding import dump_credentials
from chatballs.integrations.service_connections.services import _clean_name
from chatballs.tenancy.database import tenant_atomic


def require_enabled(organization):
    if not organization.external_execution_enabled:
        raise ValidationError(t("external.disabled"))


def audit(context, organization, action, identifier=""):
    record_audit_event(action="ai." + action, organization=organization, actor=context.actor_user,
                       object_type="ExternalAgentConfiguration", object_id=str(identifier), payload=None)


def settings(context):
    from chatballs.ai.external_agents.settings_catalog import catalog

    with tenant_atomic(context):
        organization = owner(context)
        return {"enabled": organization.external_execution_enabled,
                "version": organization.external_execution_version,
                "catalog": catalog(context),
                "connections": [connection_payload(row) for row in ExternalAgentConnection.objects.filter(
                    organization_id=context.organization_id).select_related("integration__service_settings").order_by("pk")]}


def set_feature(context, body):
    if not isinstance(body, dict) or set(body) != {"enabled"} or type(body["enabled"]) is not bool:
        invalid()
    with tenant_atomic(context):
        organization = owner(context)
        if organization.external_execution_enabled != body["enabled"]:
            organization.external_execution_enabled = body["enabled"]
            organization.save(update_fields=["external_execution_enabled"])
            if body["enabled"]:
                from chatballs.ai.external_agents.config_models import ExternalAgentBinding

                # Retain configuration and allowlists; old checks and acknowledgements
                # cannot authorize a newly enabled execution generation.
                ExternalAgentConnection.objects.filter(organization=organization).update(checked_at=None)
                ExternalAgentBinding.objects.filter(organization=organization).update(policy_accepted=False)
                Integration.objects.filter(external_execution__organization=organization).update(
                    status="UNCHECKED", last_error_code="", last_error="", last_checked_at=None)
            audit(context, organization, "external.feature_changed")
    return settings(context)


def access_values(body, *, new):
    if not isinstance(body, dict) or set(body) - {"name", "baseUrl", "outboundKey", "enabled"}:
        invalid()
    if new and set(body) != {"name", "baseUrl", "outboundKey"}:
        invalid()
    if "enabled" in body and type(body["enabled"]) is not bool:
        invalid()
    for key in ("name", "baseUrl", "outboundKey"):
        if key in body and (not isinstance(body[key], str) or not body[key].strip() or len(body[key]) > (255 if key == "name" else 4096)):
            invalid()
    if "outboundKey" in body and any(ord(char) < 33 or ord(char) > 126 for char in body["outboundKey"]):
        invalid()
    if "baseUrl" in body:
        try:
            return clean_address(body["baseUrl"])
        except ValueError:
            invalid()


def create_connection(context, body):
    address = access_values(body, new=True)
    with tenant_atomic(context):
        organization = owner(context)
        require_enabled(organization)
        integration = Integration.objects.create(organization=organization, name=_clean_name(context, body["name"]),
                                                 kind="SERVICE", provider="ADAPTER", status="UNCHECKED")
        ServiceConnectionSettings.objects.create(
            integration=integration, adapter_key=ADAPTER.key, adapter_version=1, auth_method="bearer",
            settings={"base_url": address}, credentials=dump_credentials({"token": body["outboundKey"]}),
        )
        row = ExternalAgentConnection.objects.create(
            integration=integration,
            deduplication_key=secrets.token_urlsafe(48),
        )
        audit(context, organization, "external.connection_created", row.pk)
        return {"connection": connection_payload(row)}


def update_connection(context, connection_id, body):
    from chatballs.integrations.service_connections.binding import load_credentials

    access_values(body, new=False)
    with tenant_atomic(context):
        organization = owner(context)
        require_enabled(organization)
        row = connection_for(context, connection_id, lock=True)
        service = row.integration.service_settings
        if "name" in body:
            row.integration.name = _clean_name(context, body["name"], exclude_id=row.integration_id)
            row.integration.save(update_fields=["name"])
        if "baseUrl" in body or "outboundKey" in body:
            credential = body.get("outboundKey", load_credentials(service).get("token"))
            from chatballs.ai.external_agents.auth import key_hash
            if not credential or key_hash(credential) == row.inbound_key_hash:
                invalid()
            service.settings = {"base_url": clean_address(body.get("baseUrl", service.settings["base_url"]))}
            service.credentials = dump_credentials({"token": credential})
            service.save(update_fields=["settings", "credentials"])
            row.capabilities, row.checked_at = {}, None
            row.bindings.update(policy_accepted=False)
            row.integration.status = "UNCHECKED"
            row.integration.last_error_code = row.integration.last_error = ""
            row.integration.last_checked_at = None
            row.integration.save(update_fields=["status", "last_error_code", "last_error", "last_checked_at"])
        if "enabled" in body:
            row.enabled = body["enabled"]
        row.save(update_fields=["capabilities", "checked_at", "enabled"])
        row.refresh_from_db()
        audit(context, organization, "external.connection_updated", row.pk)
        return {"connection": connection_payload(row)}
