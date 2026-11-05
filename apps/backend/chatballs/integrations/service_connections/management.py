"""Shared lifecycle commands; external checks remain outside DB transactions."""

from chatballs.identity.audit import record_audit_event
from chatballs.integrations.service_connections import management_reads as reads
from chatballs.integrations.service_connections import services
from chatballs.integrations.service_connections.binding import ServiceUnavailable, load_lookup
from chatballs.integrations.service_connections.errors import ServiceCheckFailed
from chatballs.tenancy.database import tenant_atomic

MANAGE = "integrations.manage"


class ManagementCheckFailed(Exception):
    def __init__(self, adapter, code, payload=None):
        self.adapter, self.code, self.payload = adapter, code, payload or {}
        super().__init__(code)


def access_data(body):
    data = body if isinstance(body, dict) else {}
    values = data.get("values")
    return services.AccessInput(adapter_key=str(data.get("adapter", "")),
        auth_method=str(data.get("authMethod", "")), name=str(data.get("name", "")),
        values=values if isinstance(values, dict) else {})


def audit(context, action, identifier, payload=None, request=None):
    with tenant_atomic(context):
        record_audit_event(action=action, actor=context.actor_user, organization=context.organization,
            object_type="Integration", object_id=str(identifier), payload=payload or {}, request=request)


def create(context, body, *, request=None):
    reads.require(context, MANAGE)
    data = access_data(body)
    try:
        row = services.create_connection(context=context, data=data)
    except ServiceCheckFailed as error:
        raise ManagementCheckFailed(data.adapter_key, error.code) from error
    audit(context, "integrations.service_connected", row.pk, {"adapter": data.adapter_key}, request)
    return reads.payload(context, row)


def update(context, connection_id, body, *, request=None):
    row = reads.load(context, connection_id, MANAGE)
    data = body if isinstance(body, dict) else {}
    if "name" in data:
        services.rename_connection(context=context, integration=row, name=str(data["name"]))
        audit(context, "integrations.service_renamed", row.pk, request=request)
    if isinstance(data.get("isActive"), bool):
        services.set_active(context=context, integration=row, active=data["isActive"])
        action = "integrations.service_resumed" if data["isActive"] else "integrations.service_paused"
        audit(context, action, row.pk, request=request)
    return reads.payload(context, row)


def delete(context, connection_id, *, request=None):
    row = reads.load(context, connection_id, MANAGE)
    services.delete_connection(context=context, integration=row)
    audit(context, "integrations.service_deleted", connection_id, request=request)
    return {}


def check(context, connection_id, body, *, request=None):
    row = reads.load(context, connection_id, MANAGE)
    inputs = body.get("inputs") if isinstance(body, dict) else None
    failure = None
    try:
        services.check_connection(context=context, integration=row,
            inputs=inputs if isinstance(inputs, dict) else None)
    except ServiceCheckFailed as error:
        failure = error
    audit(context, "integrations.service_checked", row.pk, {"ok": failure is None}, request)
    payload = reads.payload(context, row)
    if failure:
        raise ManagementCheckFailed(row.service_settings.adapter_key, failure.code, payload) from failure
    return payload


def replace_access(context, connection_id, body, *, request=None):
    row = reads.load(context, connection_id, MANAGE)
    values = body.get("values") if isinstance(body, dict) else None
    try:
        services.replace_access(context=context, integration=row, values=values if isinstance(values, dict) else {})
    except ServiceCheckFailed as error:
        raise ManagementCheckFailed(row.service_settings.adapter_key, error.code) from error
    audit(context, "integrations.service_access_replaced", row.pk, request=request)
    return reads.payload(context, row)


def lookup(context, connection_id, key):
    row = reads.load(context, connection_id, MANAGE)
    try:
        items = load_lookup(tenant=context, integration=row, key=key)
    except ServiceUnavailable as error:
        raise ManagementCheckFailed(row.service_settings.adapter_key, error.code) from error
    return {"items": [{"value": item.value, "label": item.label} for item in items]}

