"""Organization settings reuse product commands; credentials never become output."""

from functools import partial

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import NotFound

from chatballs.ai.diagnostic_redaction import integration_secrets
from chatballs.i18n import t
from chatballs.identity import organization_settings_commands as commands
from chatballs.identity.audit_queries import list_audit
from chatballs.identity.demo_seed import service as demo_service
from chatballs.identity.onboarding_services import change_onboarding, onboarding_status
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied
from chatballs.integrations.action_catalog.file_reads import FILE_RESULT, stream_result
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.action_catalog.settings_schemas import (
    AUDIT,
    AUDIT_INPUT,
    COMMUNICATION,
    COMMUNICATION_INPUT,
    DEMO,
    EDIT,
    ONBOARDING,
    ONBOARDING_INPUT,
    OUTPUT,
    READ,
    field,
)
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.communication_settings import read_communication, update_communication
from chatballs.integrations.execution.payloads import clean_value
from chatballs.integrations.models import Integration
from chatballs.tenancy.database import tenant_atomic


def query(context, values, *, service, body=False):
    result = service(context.tenant, values) if body else service(context.tenant)
    return OperationResult(ResultState.COMPLETED, result)


def audit(context, values):
    result = list_audit(context.tenant, values)
    secrets = integration_secrets(Integration.objects.filter(organization_id=context.tenant.organization_id))
    for item in result["items"]:
        item["details"] = clean_value(None, item["details"], secrets)
    return OperationResult(ResultState.COMPLETED, result)


def logo(context, values, *, operation):
    with tenant_atomic(context.tenant):
        if operation == "read":
            try:
                file, content_type = commands.read_logo(context.tenant)
            except NotFound:
                raise NativeAccessDenied("context") from None
            stream = file.open("rb")
        elif operation == "upload":
            name, content_type, content = context.open_file(values["file"]["fileId"])
            result = commands.upload_logo(context.tenant, SimpleUploadedFile(name, content, content_type))
        else:
            result = commands.remove_logo(context.tenant)
    if operation == "read":
        return stream_result(context, stream, "organization-logo", content_type)
    return OperationResult(ResultState.COMPLETED, result)


def demo(context, values, *, command=None):
    if command:
        command(context=context.tenant, actor=context.tenant.actor_user)
    result = demo_service.demo_status(context.tenant.organization)
    # The ordinary demo login form keeps its public demonstration credential.
    # Automation receives account metadata, never a usable password.
    result["accounts"] = [{key: value for key, value in row.items() if key != "password"}
        for row in result["accounts"]]
    # Worker exceptions can contain storage/provider credentials. Only the
    # confirmed failure status belongs in the automation result, not raw text.
    if result["error"]:
        result["error"] = t("native.settings.demo_status.FAILED")
    return OperationResult(ResultState.COMPLETED, result)


for key, inputs, outputs, handler, method, route, module, view, capability, effect, execution in (
    ("settings.get", obj(), READ, partial(query, service=commands.read_settings), "GET", "administration/", "identity.administration_views", "OrganizationSettingsView", "settings.view", Effect.READ, "local"),
    ("settings.patch", obj(**EDIT), OUTPUT, partial(query, service=commands.update_settings, body=True), "PATCH", "administration/", "identity.administration_views", "OrganizationSettingsView", "settings.manage", Effect.UPDATE, "local"),
    ("settings.logo.get", obj(), FILE_RESULT, partial(logo, operation="read"), "GET", "administration/logo/", "identity.administration_views", "OrganizationLogoView", "", Effect.READ, "io"),
    ("settings.logo.post", obj(file=field("file", "file", required=True)), OUTPUT, partial(logo, operation="upload"), "POST", "administration/logo/", "identity.administration_views", "OrganizationLogoView", "settings.manage", Effect.UPDATE, "io"),
    ("settings.logo.delete", obj(), OUTPUT, partial(logo, operation="delete"), "DELETE", "administration/logo/", "identity.administration_views", "OrganizationLogoView", "settings.manage", Effect.DELETE, "io"),
    ("settings.audit.get", AUDIT_INPUT, AUDIT, audit, "GET", "administration/audit/", "identity.administration_views", "AuditListView", "audit.view", Effect.READ, "local"),
    ("settings.onboarding.get", obj(), ONBOARDING, partial(query, service=onboarding_status), "GET", "onboarding/", "identity.onboarding_views", "OnboardingView", "settings.view", Effect.READ, "local"),
    ("settings.onboarding.post", ONBOARDING_INPUT, ONBOARDING, partial(query, service=change_onboarding, body=True), "POST", "onboarding/", "identity.onboarding_views", "OnboardingView", "settings.view", Effect.UPDATE, "local"),
    ("settings.communication.get", obj(), COMMUNICATION, partial(query, service=read_communication), "GET", "administration/communication/", "integrations.feature_views", "CommunicationSettingsView", "settings.view", Effect.READ, "local"),
    ("settings.communication.patch", COMMUNICATION_INPUT, COMMUNICATION, partial(query, service=update_communication, body=True), "PATCH", "administration/communication/", "integrations.feature_views", "CommunicationSettingsView", "company.manage", Effect.UPDATE, "local"),
    ("settings.demo.get", obj(), DEMO, demo, "GET", "demo/", "identity.demo_views", "DemoDataView", "settings.view", Effect.READ, "local"),
    ("settings.demo.post", obj(), DEMO, partial(demo, command=demo_service.request_install), "POST", "demo/", "identity.demo_views", "DemoDataView", "company.manage", Effect.CREATE, "local"),
    ("settings.demo.delete", obj(), DEMO, partial(demo, command=demo_service.request_remove), "DELETE", "demo/", "identity.demo_views", "DemoDataView", "company.manage", Effect.DELETE, "local"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs, handler=handler,
        capability=capability, scope="organization", route=f"company/{route}",
        view=f"chatballs.{module}.{view}", method=method, effect=effect, execution=execution)
