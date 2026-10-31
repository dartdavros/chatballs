"""Typed input file ownership survives the source run's retention window."""

from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.files import ServiceFile
from chatballs.integrations.scenario_state.retention import StepOperationalFile


def file_references(spec, value):
    if spec.type == "file" and isinstance(value, dict):
        return {str(value["fileId"])}
    if spec.type == "object" and isinstance(value, dict):
        return set().union(*(file_references(child, value[name]) for name, child in spec.properties if name in value))
    if spec.type == "array" and spec.items and isinstance(value, list):
        return set().union(*(file_references(spec.items, child) for child in value))
    return set()


def lock_input_files(tenant, operation, arguments):
    ids = file_references(operation.input, arguments)
    files = list(ServiceFile.objects.select_for_update().filter(organization_id=tenant.organization_id, public_id__in=ids))
    if {str(file.public_id) for file in files} != ids:
        raise ExecutionDenied("arguments")
    return files


def own_input_files(step, files):
    for file in files:
        StepOperationalFile.objects.get_or_create(organization_id=step.organization_id, step=step, file=file)
