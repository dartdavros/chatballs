"""Assignment policy, reason catalog and protected transfer history actions."""

from dataclasses import replace

from rest_framework.exceptions import NotFound

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.assignment_policy import assignment_settings
from chatballs.conversations.transfer_queries import transfer_history, transfer_options
from chatballs.conversations.transfer_reason_inputs import ReasonInput
from chatballs.conversations.transfer_reason_payloads import reason_payload
from chatballs.conversations.transfer_services import (
    disable_reason,
    reasons_for_management,
    save_reason,
)
from chatballs.i18n import t
from chatballs.integrations.action_catalog.contracts import APIEntry
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    CONVERSATION_ID,
    IDENTIFIER,
    action,
    obj,
    required,
)
from chatballs.integrations.action_catalog.transfer_schemas import (
    HISTORY_TRANSFER,
    POLICY_INPUT,
    POLICY_RESULT,
    REASON,
    REASON_OPTION,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec

NAME = TypeSpec("string", max_length=120)
CODE = TypeSpec("string", max_length=64, pattern="[-a-zA-Z0-9_]+")


def result(value):
    return OperationResult(ResultState.COMPLETED, value)


def policy(context, values):
    return result(assignment_settings(context.tenant))


def update_policy(context, values):
    return result(assignment_settings(context.tenant, values))


def history(context, values):
    return result(transfer_history(context.tenant, values["conversation_id"], values,
        transfer_id=values.get("transfer_id")))


def options(context, values):
    return result(transfer_options(context.tenant, values["conversation_id"], values))


def reasons(context, values):
    return result(page_payload(paginate(reasons_for_management(context.tenant), values), reason_payload))


def reason(context, values):
    row = reasons_for_management(context.tenant).filter(pk=values["reason_id"]).first()
    if row is None:
        raise NotFound(t("transfers.reason_not_found"))
    return result({"reason": reason_payload(row)})


def _save(context, values, *, updating):
    data = {key: values[key] for key in ("name", "code", "isActive") if key in values}
    serializer = ReasonInput(data=data, partial=updating)
    serializer.is_valid(raise_exception=True)
    row = save_reason(context=context.tenant, data=serializer.validated_data,
        reason_id=values["reason_id"] if updating else None)
    row = reasons_for_management(context.tenant).get(pk=row.pk)
    return result({"reason": reason_payload(row)})


def create_reason(context, values):
    return _save(context, values, updating=False)


def update_reason(context, values):
    return _save(context, values, updating=True)


def delete_reason(context, values):
    disable_reason(context=context.tenant, reason_id=values["reason_id"])
    return result({})


for key, title, inputs, output, handler, method, route, view in (
    ("conversations.assignment_policy.get", "native.assignment_policy", obj(), POLICY_RESULT,
        policy, "GET", "assignment-policy/", "AssignmentPolicyView"),
    ("conversations.assignment_policy.put", "native.assignment_policy_update", POLICY_INPUT, POLICY_RESULT,
        update_policy, "PUT", "assignment-policy/", "AssignmentPolicyView"),
    ("transfers.options.get", "native.transfer_options", obj(conversation_id=CONVERSATION_ID, **PAGE_INPUTS),
        page_of(REASON_OPTION), options, "GET", "<int:conversation_id>/transfer-options/", "TransferOptionsView"),
    ("transfers.reasons.get", "native.transfer_reasons", obj(**PAGE_INPUTS), page_of(REASON),
        reasons, "GET", "transfer-reasons/", "ReasonListView"),
    ("transfers.reasons.post", "native.transfer_reason_create", obj(name=required(NAME), code=CODE, isActive=BOOLEAN),
        obj(reason=REASON), create_reason, "POST", "transfer-reasons/", "ReasonListView"),
    ("transfers.reason.get", "native.transfer_reason", obj(reason_id=IDENTIFIER), obj(reason=REASON),
        reason, "GET", "transfer-reasons/<int:reason_id>/", "ReasonDetailView"),
    ("transfers.reason.patch", "native.transfer_reason_update", obj(reason_id=IDENTIFIER, name=NAME, code=CODE, isActive=BOOLEAN),
        obj(reason=REASON), update_reason, "PATCH", "transfer-reasons/<int:reason_id>/", "ReasonDetailView"),
    ("transfers.reason.delete", "native.transfer_reason_delete", obj(reason_id=IDENTIFIER), obj(),
        delete_reason, "DELETE", "transfer-reasons/<int:reason_id>/", "ReasonDetailView"),
):
    reason_view = view.startswith("Reason")
    action(key=key, title=title, input=inputs, output=output, handler=handler, method=method,
        route=f"conversations/{route}", view=f"chatballs.conversations.{'transfer_reason_views' if reason_view else 'transfer_views'}.{view}",
        capability="conversations.assign" if handler is options else "settings.manage",
        scope="conversation" if handler is options else "organization")

action(key="transfers.history.get", title="native.transfer_history",
    input=obj(conversation_id=CONVERSATION_ID, transfer_id=replace(IDENTIFIER, required=False), **PAGE_INPUTS),
    output=replace(page_of(HISTORY_TRANSFER), properties=page_of(HISTORY_TRANSFER).properties + obj(transfer=HISTORY_TRANSFER).properties),
    handler=history, method="GET", route="conversations/<int:conversation_id>/transfers/",
    view="chatballs.conversations.transfer_views.TransferHistoryView", capability="conversations.view", scope="conversation",
    extra_entries=(APIEntry("conversations/<int:conversation_id>/transfers/<int:transfer_id>/", "GET",
        "chatballs.conversations.transfer_views.TransferHistoryView"),))
