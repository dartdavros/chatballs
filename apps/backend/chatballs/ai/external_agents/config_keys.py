"""Read-only compatibility checks, explicit rotation and revocation."""

import secrets

from django.utils import timezone

from chatballs.ai.external_agents.adapter import check_capabilities
from chatballs.ai.external_agents.config import audit, require_enabled
from chatballs.ai.external_agents.config_access import (
    connection_for,
    connection_payload,
    owner,
)
from chatballs.ai.external_agents.config_policy import invalid
from chatballs.integrations.adapters.transport import TransportError
from chatballs.integrations.service_connections.binding import load_credentials
from chatballs.tenancy.database import tenant_atomic


def check_connection(context, connection_id):
    with tenant_atomic(context):
        organization = owner(context)
        require_enabled(organization)
        row = connection_for(context, connection_id)
        if not row.enabled:
            invalid()
        version = (organization.external_execution_version, row.revision)
        service = row.integration.service_settings
        address, credential = service.settings["base_url"], load_credentials(service)["token"]
    try:
        capabilities = check_capabilities(address, credential)
    except TransportError as error:
        with tenant_atomic(context):
            organization = owner(context)
            row = connection_for(context, connection_id, lock=True)
            if version == (organization.external_execution_version, row.revision):
                row.capabilities, row.checked_at = {}, None
                row.save(update_fields=["capabilities", "checked_at"])
                row.integration.status = "ERROR"
                row.integration.last_error_code = {"capabilities_access_denied": "access",
                    "incompatible_capabilities": "incompatible"}.get(error.code, "unavailable")
                row.integration.last_error = ""
                row.integration.last_checked_at = timezone.now()
                row.integration.save(update_fields=["status", "last_error_code", "last_error", "last_checked_at"])
        raise
    with tenant_atomic(context):
        organization = owner(context)
        require_enabled(organization)
        row = connection_for(context, connection_id, lock=True)
        if version != (organization.external_execution_version, row.revision):
            invalid()
        row.capabilities, row.checked_at = capabilities, timezone.now()
        row.save(update_fields=["capabilities", "checked_at"])
        row.refresh_from_db()
        row.integration.status = "OK"
        row.integration.last_error_code = row.integration.last_error = ""
        row.integration.last_checked_at = row.checked_at
        row.integration.save(update_fields=["status", "last_error_code", "last_error", "last_checked_at"])
        audit(context, organization, "external.connection_checked", row.pk)
        return {"connection": connection_payload(row)}


def change_key(context, connection_id, *, revoke=False):
    from chatballs.ai.external_agents.auth import key_hash

    with tenant_atomic(context):
        organization = owner(context)
        row = connection_for(context, connection_id, lock=True)
        if not revoke:
            require_enabled(organization)
        token = None if revoke else secrets.token_urlsafe(48)
        row.inbound_key_hash = None if token is None else key_hash(token)
        row.save(update_fields=["inbound_key_hash"])
        row.refresh_from_db()
        audit(context, organization, "external.key_revoked" if revoke else "external.key_rotated", row.pk)
        payload = {"connection": connection_payload(row)}
        if token:
            payload["incomingKey"] = token
        return payload
