"""Shared definition management; saving never acts as an invocation protocol."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios import presets, services
from chatballs.integrations.scenarios.catalog import definition_context
from chatballs.integrations.scenarios.categories import UNSET_CATEGORY_PATH
from chatballs.integrations.scenarios.external_keys import key_payload, synchronize_keys
from chatballs.integrations.scenarios.payloads import issue_payload, scenario_payload
from chatballs.integrations.scenarios.validation import validate_definition
from chatballs.integrations.service_connections.management_reads import require
from chatballs.tenancy.database import tenant_atomic


class InvalidDefinition(Exception):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("arguments")


def rows(tenant):
    require(tenant, "integrations.manage")
    return ScenarioDefinition.objects.filter(organization_id=tenant.organization_id)


def audit(tenant, row, action, request=None):
    record_audit_event(action=f"integrations.scenario_{action}", actor=tenant.actor_user,
        organization=tenant.organization, object_type="ScenarioDefinition", object_id=str(row.public_id),
        payload={"revision": row.revision}, request=request)


def payload(row, *, issues=None, request=None, synchronize=False):
    result = scenario_payload(row, issues=issues)
    # Native calls obtain metadata only. The existing interactive rotate-key
    # protocol can issue a usable token; credentials are never ordinary output.
    result["externalKeys"] = synchronize_keys(request, row) if synchronize else [
        key_payload(request, key) for key in row.external_keys.all()]
    return {"scenario": result}


def listing(tenant, *, connection=""):
    with tenant_atomic(tenant):
        query = rows(tenant).order_by("name", "id")
        if connection:
            if not str(connection).isdecimal():
                raise ScenarioDefinition.DoesNotExist()
            query = query.filter(connections__integration_id=int(connection))
        return {"items": [scenario_payload(row, detail=False) for row in query]}


def detail(tenant, public_id, *, request=None):
    with tenant_atomic(tenant):
        row = rows(tenant).get(public_id=public_id)
        issues = validate_definition(row.definition, context=definition_context(row.organization_id, excluding=public_id))
        return payload(row, issues=issues, request=request)


def save(tenant, data, *, public_id=None, request=None):
    require(tenant, "integrations.manage")
    allowed = {"name", "definition", "revision", "enabled", "agentPolicies", "categoryPath"}
    if not isinstance(data, dict) or set(data) - allowed or not isinstance(data.get("enabled", False), bool):
        raise ValidationError({"definition": t("scenarios.invalid_definition")})
    with tenant_atomic(tenant):
        row, issues = services.save_definition(tenant=tenant, name=data.get("name"),
            document=data.get("definition"), revision=data.get("revision"), public_id=public_id,
            enabled=data.get("enabled", False),
            category_path=data.get("categoryPath", UNSET_CATEGORY_PATH))
        if row is None:
            raise InvalidDefinition(issues)
        if "agentPolicies" in data:
            from chatballs.integrations.execution.scenario_agent_policies import (
                save as save_policies,
            )
            save_policies(tenant, row, data["agentPolicies"])
        audit(tenant, row, "saved", request)
        return payload(row, issues=issues, request=request, synchronize=True)


def delete(tenant, public_id, revision, *, request=None):
    with tenant_atomic(tenant):
        row = rows(tenant).get(public_id=public_id)
        services.delete_definition(tenant=tenant, public_id=public_id, revision=revision)
        audit(tenant, row, "deleted", request)
        return {}


def check(tenant, document):
    require(tenant, "integrations.manage")
    with tenant_atomic(tenant):
        issues = validate_definition(document, context=definition_context(tenant.organization_id))
        return {"issues": [issue_payload(issue) for issue in issues], "valid": not issues}


def copy(tenant, public_id, name, *, request=None):
    require(tenant, "integrations.manage")
    with tenant_atomic(tenant):
        row, issues = services.copy_definition(tenant=tenant, source=public_id, name=name)
        audit(tenant, row, "copied", request)
        return payload(row, issues=issues, request=request, synchronize=True)


def preset(tenant, connection_id, key, *, request=None):
    require(tenant, "integrations.manage")
    with tenant_atomic(tenant):
        row, issues = presets.copy_preset(tenant=tenant, connection_id=connection_id, key=key)
        audit(tenant, row, "copied", request)
        return payload(row, issues=issues, request=request, synchronize=True)
