"""Atomic editing with an optimistic revision; saving is never a launch/grant."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.integrations.adapters.schema import SchemaDefinitionError
from chatballs.integrations.models import Integration
from chatballs.integrations.scenario_state.definitions import ScenarioConnection, ScenarioDefinition
from chatballs.integrations.scenarios.catalog import connection_ids, definition_context
from chatballs.integrations.scenarios.categories import UNSET_CATEGORY_PATH
from chatballs.integrations.scenarios.categories import category_path as normalize_category_path
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.scenarios.validation import validate_definition
from chatballs.tenancy.database import tenant_atomic


class RevisionConflict(Exception):
    pass


def save_definition(*, tenant, name, document, public_id=None, revision=None, enabled=False,
                    category_path=UNSET_CATEGORY_PATH):
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 200:
        raise ValidationError({"name": t("scenarios.name_required")})
    if not isinstance(document, dict) or set(document) != set(empty_definition()):
        raise ValidationError({"definition": t("scenarios.invalid_definition")})
    if category_path is not UNSET_CATEGORY_PATH:
        category_path = normalize_category_path(category_path)
    # Even an unfinished disabled draft must use the one versioned format.
    try:
        if document["version"] != 1:
            raise ValueError("version")
        read_type(document["parameters"])
        read_type(document["results"])
    except (ValueError, TypeError, SchemaDefinitionError):
        raise ValidationError({"definition": t("scenarios.invalid_definition")}) from None
    with tenant_atomic(tenant):
        row = None
        if public_id:
            row = ScenarioDefinition.objects.select_for_update().get(public_id=public_id, organization_id=tenant.organization_id)
            if type(revision) is not int or row.revision != revision:
                raise RevisionConflict
        context = definition_context(tenant.organization_id, excluding=public_id)
        issues = validate_definition(document, context=context)
        if any(issue.code in {"structure", "unknown", "version", "schema", "block", "trigger", "identifier", "size", "binding"} for issue in issues):
            from chatballs.integrations.scenarios.management import InvalidDefinition
            raise InvalidDefinition(issues)
        if enabled and issues:
            return None, issues
        connections = connection_ids(document)
        found = set(Integration.objects.filter(organization_id=tenant.organization_id, pk__in=connections).values_list("id", flat=True))
        if found != connections:
            raise ValidationError({"definition": t("scenarios.invalid_reference")})
        previous = row.definition if row else {}
        if row is None:
            row = ScenarioDefinition(organization_id=tenant.organization_id)
        else:
            row.revision += 1
        row.name = name.strip()
        if category_path is not UNSET_CATEGORY_PATH:
            row.category_path = category_path
        row.definition = document
        row.enabled = enabled
        row.save()
        from chatballs.integrations.automation_events.configuration import synchronize
        synchronize(tenant, row, previous)
        row.connections.exclude(integration_id__in=connections).delete()
        for connection in connections:
            ScenarioConnection.objects.get_or_create(organization_id=tenant.organization_id, scenario=row, integration_id=connection)
        return row, issues


def copy_definition(*, tenant, source, name):
    with tenant_atomic(tenant):
        row = ScenarioDefinition.objects.get(organization_id=tenant.organization_id, public_id=source)
        document = row.definition
        document["access"]["delegated"] = False
        copied, issues = save_definition(tenant=tenant, name=name, document=document,
                                        category_path=row.category_path)
        return copied, issues


def delete_definition(*, tenant, public_id, revision):
    with tenant_atomic(tenant):
        row = ScenarioDefinition.objects.select_for_update().get(organization_id=tenant.organization_id, public_id=public_id)
        if type(revision) is not int or revision != row.revision:
            raise RevisionConflict
        row.delete()
