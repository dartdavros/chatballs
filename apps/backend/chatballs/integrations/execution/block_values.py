"""Lexical frame values and durable error data, without copying credentials."""

from copy import deepcopy
from dataclasses import asdict

from chatballs.integrations.execution.permissions import allowed_files
from chatballs.integrations.scenarios.values import RunValues


def initial(run):
    data = run.definition
    return asdict(RunValues(parameters=data["parameters"], context=data.get("context", {}),
                            event=data.get("event", {}), files=set())) | {"files": []}


def actual(tenant, run, data):
    if tenant.membership is None and run.initiator_id:
        from chatballs.tenancy.context import TenantContext
        tenant = TenantContext.for_membership(run.initiator)
    value = deepcopy(data)
    value["files"] = {str(pk) for pk in allowed_files(tenant, run.conversation_id).values_list("public_id", flat=True)}
    return RunValues(**value)


def error_data(run, frame):
    data = frame.definition
    return data.get("error") or {"reason": frame.error_code or "operation_rejected",
        "step": data.get("block", {}).get("name") or data.get("block", {}).get("id", ""),
        "service": data.get("service", ""), "run": str(run.pk), "number": data.get("number", 1)}
