"""Availability uses the existing self identity and supervised read boundary."""

from chatballs.identity.work_status_access import readable_membership, work_status_history
from chatballs.identity.work_status_payloads import operation_payload, status_payload
from chatballs.identity.work_status_services import change_work_status
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

STATUS = TypeSpec("enum", title_key="native.availability.status", options=tuple(
    EnumOption(code, f"work_status.label.{code.lower()}") for code in ("READY", "BUSY", "BREAK", "UNAVAILABLE")))
VERSION = TypeSpec("integer", title_key="native.availability.version")
STAMP = TypeSpec("datetime", nullable=True, title_key="native.availability.changed_at")
OPERATION_ID = TypeSpec("string", title_key="native.availability.operation_id")
USER_ID = TypeSpec("integer", required=True, title_key="native.availability.employee")
CURRENT = obj(status=STATUS, version=VERSION, changedAt=STAMP)
OPERATION = obj(status=STATUS, version=VERSION, changedAt=STAMP, operationId=OPERATION_ID,
    previousStatus=STATUS, recordedAt=TypeSpec("datetime", title_key="native.availability.recorded_at"),
    changed=TypeSpec("boolean", title_key="native.availability.changed"))


def current(context, values):
    member = readable_membership(context=context.tenant, user_id=values.get("user_id"))
    return OperationResult(ResultState.COMPLETED, status_payload(member))


def history(context, values):
    return OperationResult(ResultState.COMPLETED, work_status_history(
        context=context.tenant, params=values, user_id=values.get("user_id")))


def change(context, values):
    operation = change_work_status(context=context.tenant, status=values["status"],
        expected_version=values["expectedVersion"], operation_id=values["operationId"])
    return OperationResult(ResultState.COMPLETED, operation_payload(operation))


for key, inputs, outputs, handler, method, route, view in (
    ("availability.own.get", obj(), CURRENT, current, "GET", "me/work-status/", "OwnWorkStatusView"),
    ("availability.own.post", obj(status=required(STATUS), expectedVersion=required(VERSION),
        operationId=required(OPERATION_ID)), OPERATION, change, "POST", "me/work-status/", "OwnWorkStatusView"),
    ("availability.employee.get", obj(user_id=USER_ID), CURRENT, current, "GET",
        "<int:user_id>/work-status/", "EmployeeWorkStatusView"),
    ("availability.own.history.get", obj(**PAGE_INPUTS), page_of(OPERATION), history, "GET",
        "me/work-status/history/", "WorkStatusHistoryView"),
    ("availability.employee.history.get", obj(user_id=USER_ID, **PAGE_INPUTS), page_of(OPERATION),
        history, "GET", "<int:user_id>/work-status/history/", "WorkStatusHistoryView"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs, handler=handler,
        capability="", scope="organization", route=f"employees/{route}",
        view=f"chatballs.identity.work_status_views.{view}", method=method)
