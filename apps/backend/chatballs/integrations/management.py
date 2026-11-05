"""Application commands for transport, AI and external-server connections."""

from django.core.exceptions import ValidationError

from chatballs.integrations import services
from chatballs.integrations.deletion import delete_integration
from chatballs.integrations.external_server import validate_http_address
from chatballs.integrations.external_tools import refresh_tools
from chatballs.integrations.management_inputs import integration_input
from chatballs.integrations.read_only import confirm_read_only, revoke_read_only
from chatballs.integrations.selectors import integration_for_context, integrations_for_context
from chatballs.integrations.serializers import integration_payload
from chatballs.integrations.service_connections.management import audit
from chatballs.integrations.service_connections.management_reads import require
from chatballs.tenancy.database import tenant_atomic


def load(context, integration_id):
    require(context, "integrations.manage")
    return integration_for_context(context=context, integration_id=integration_id)


def listing(context):
    require(context)
    with tenant_atomic(context):
        return {"items": [integration_payload(row) for row in integrations_for_context(context)]}


def create(context, body, *, request=None):
    require(context, "integrations.manage")
    with tenant_atomic(context):
        row = services.create_integration(context=context, data=integration_input(body))
        audit(context, "integrations.integration_created", row.pk, request=request)
        return {"integration": integration_payload(row)}


def update(context, integration_id, body, *, request=None):
    with tenant_atomic(context):
        row = load(context, integration_id)
        row = services.update_integration(context=context, integration=row,
            data=integration_input(body, current=row))
        audit(context, "integrations.integration_updated", row.pk, request=request)
        return {"integration": integration_payload(row)}


def delete(context, integration_id, *, request=None):
    with tenant_atomic(context):
        row = load(context, integration_id)
        delete_integration(context=context, integration=row)
        audit(context, "integrations.integration_deleted", integration_id, request=request)
        return {}


def checked(context, integration_id, body=None, *, refresh=False, request=None):
    from chatballs.speech.checking import finish_check, prepare_check, run_check

    with tenant_atomic(context):
        row = load(context, integration_id)
        if refresh or row.provider != "YANDEX_SPEECHKIT":
            operation = refresh_tools if refresh else services.test_integration
            row = operation(context=context, integration=row)
            audit(context, "integrations.tools_refreshed" if refresh else "integrations.integration_tested",
                row.pk, request=request)
            return {"integration": integration_payload(row)}
        job = prepare_check(row, (body or {}).get("capability", "stt"))
    error_code = run_check(job)
    with tenant_atomic(context):
        require(context, "integrations.manage")
        row = finish_check(context, job, error_code)
        audit(context, "integrations.integration_tested", row.pk, request=request)
        return {"integration": integration_payload(row)}


def read_only(context, integration_id, body, *, revoke=False, request=None):
    with tenant_atomic(context):
        row = load(context, integration_id)
        name = body.get("name")
        kwargs = {} if revoke else {"confirmed": body.get("confirmed")}
        operation = revoke_read_only if revoke else confirm_read_only
        operation(context=context, integration=row, name=name, actor=context.actor_user, **kwargs)
        audit(context, "integrations.tool_read_only_revoked" if revoke else "integrations.tool_read_only_confirmed",
            row.pk, {"tool": name}, request)
        return {"integration": integration_payload(row)}


def address(context, body):
    require(context, "integrations.manage")
    try:
        validate_http_address(str(body.get("url") or "").strip())
    except ValidationError as error:
        return {"errors": error.message_dict}
    return {"errors": {}}
