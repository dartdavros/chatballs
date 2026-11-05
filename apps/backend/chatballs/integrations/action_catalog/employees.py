"""Native employee operations reuse governance and never issue passwords to steps."""

from dataclasses import replace
from functools import partial

from rest_framework.exceptions import NotFound

from chatballs.identity import employee_invitation_commands as invitations
from chatballs.identity import employee_queries as queries
from chatballs.identity import employee_security_commands as security
from chatballs.identity.employee_creation import create_employee
from chatballs.identity.employee_updates import update_employee
from chatballs.identity.ownership_commands import transfer_ownership
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied
from chatballs.integrations.action_catalog.employee_schemas import (
    ASSIGNABLE,
    EDIT,
    EMPLOYEE,
    FILTERS,
    ID,
    OUTPUT,
    PAGE,
    field,
)
from chatballs.integrations.action_catalog.file_reads import FILE_RESULT, stream_result
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.tenancy.database import tenant_atomic


def listing(context, values):
    return OperationResult(ResultState.COMPLETED, queries.list_employees(context.tenant, values))


def detail(context, values):
    return OperationResult(ResultState.COMPLETED, queries.employee_detail(context.tenant, values["user_id"]))


def avatar(context, values):
    with tenant_atomic(context.tenant):
        try:
            file, content_type = queries.employee_avatar(context.tenant, values["user_id"])
        except NotFound:
            raise NativeAccessDenied("context") from None
        stream = file.open("rb")
    return stream_result(context, stream, "avatar", content_type)


def command(context, values, *, service, target=None, body=True, mail=False):
    args = [context.tenant]
    if target:
        args.append(values[target])
    if body:
        # One-time display is an authentication protocol, never a scenario result.
        args.append({**values, "passwordMode": "mail", "mode": "mail"} if mail else values)
    outcome = service(*args)
    if outcome.problem:
        code = {"forbidden": "permission", "invalid": "arguments", "not_found": "context",
            "conflict": "context_changed"}[outcome.problem]
        return OperationResult(ResultState.FAILED, error_code=code)
    result = {key: value for key, value in outcome.data.items() if key != "password"}
    return OperationResult(ResultState.COMPLETED, result)


for key, inputs, outputs, handler, method, route, module, view, capability, effect, execution in (
    ("employees.get", FILTERS, PAGE, listing, "GET", "", "employee_views", "EmployeeListView", "employees.view", Effect.READ, "local"),
    ("employees.detail.get", obj(user_id=ID), OUTPUT, detail, "GET", "<int:user_id>/", "employee_views", "EmployeeDetailView", "employees.view", Effect.READ, "local"),
    ("employees.avatar.get", obj(user_id=ID), FILE_RESULT, avatar, "GET", "<int:user_id>/avatar/", "employee_views", "EmployeeAvatarView", "", Effect.READ, "io"),
    ("employees.post", obj(**{**EDIT, "positionTitle": required(EDIT["positionTitle"])}),
        obj(employee=EMPLOYEE, invited=field("invited", "boolean")), partial(command, service=create_employee, mail=True),
        "POST", "operators/", "employee_views", "EmployeeCreateView", "employees.manage", Effect.CREATE, "local"),
    ("employees.update", obj(user_id=ID, **EDIT, supervisedGroupIds=field("supervisedGroups", "array", items=TypeSpec("integer"))),
        OUTPUT, partial(command, service=update_employee, target="user_id"), "POST", "<int:user_id>/update/", "employee_update_views", "EmployeeUpdateView", "employees.manage", Effect.UPDATE, "local"),
    ("employees.reset_password", obj(user_id=ID), OUTPUT, partial(command, service=security.reset_password, target="user_id", mail=True),
        "POST", "<int:user_id>/reset-password/", "employee_security_views", "EmployeeResetPasswordView", "employees.manage", Effect.UPDATE, "local"),
    ("employees.revoke_sessions", obj(user_id=ID), obj(employee=EMPLOYEE, revoked=field("revoked", "integer")),
        partial(command, service=security.revoke_sessions, target="user_id"), "POST", "<int:user_id>/revoke-sessions/", "employee_security_views", "EmployeeRevokeSessionsView", "employees.manage", Effect.DELETE, "local"),
    ("employees.block", obj(user_id=ID), OUTPUT, partial(command, service=security.block_employee, target="user_id"),
        "POST", "<int:user_id>/block/", "employee_security_views", "EmployeeBlockView", "employees.manage", Effect.UPDATE, "local"),
    ("employees.unblock", obj(user_id=ID), OUTPUT, partial(command, service=security.unblock_employee, target="user_id"),
        "POST", "<int:user_id>/unblock/", "employee_security_views", "EmployeeUnblockView", "employees.manage", Effect.UPDATE, "local"),
    ("employees.transfer_ownership", obj(user_id=ID, previousOwnerRole=replace(ASSIGNABLE, title_key="native.employee.previousOwnerRole")),
        obj(employee=EMPLOYEE, previousOwner=replace(EMPLOYEE, title_key="native.employee.previousOwner")),
        partial(command, service=transfer_ownership, target="user_id"), "POST", "<int:user_id>/transfer-ownership/", "ownership_views", "OwnershipTransferView", "employees.manage", Effect.UPDATE, "local"),
    ("employees.invitation.resend", obj(invitation_id=field("invitation", "integer", required=True)), obj(ok=TypeSpec("boolean")),
        partial(command, service=invitations.resend, target="invitation_id", body=False), "POST", "invitations/<int:invitation_id>/resend/", "employee_invitations", "InvitationResendView", "employees.manage", Effect.OTHER, "local"),
    ("employees.invitation.revoke", obj(invitation_id=field("invitation", "integer", required=True)), obj(ok=TypeSpec("boolean")),
        partial(command, service=invitations.revoke, target="invitation_id", body=False), "POST", "invitations/<int:invitation_id>/revoke/", "employee_invitations", "InvitationRevokeView", "employees.manage", Effect.UPDATE, "local"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs, handler=handler,
        capability=capability, scope="organization", route=f"employees/{route}",
        view=f"chatballs.identity.{module}.{view}", method=method, effect=effect, execution=execution)
