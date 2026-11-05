"""Employee and invitation payloads, without credential output fields."""

from dataclasses import replace

from chatballs.identity.audit_catalog import AUDIT_ACTION_LABELS
from chatballs.integrations.action_catalog.availability import CURRENT, STATUS
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import enum, obj
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec


def field(name, kind="string", **kwargs):
    return TypeSpec(kind, title_key=f"native.employee.{name}", **kwargs)


ROLE = enum(("OWNER", "ADMIN", "SUPERVISOR", "EMPLOYEE"), "native.employee_role")
ASSIGNABLE = replace(ROLE, options=ROLE.options[1:])
ID = field("employee", "integer", required=True)
GROUP = obj(id=TypeSpec("integer"), name=TypeSpec("string"))
GROUPS = TypeSpec("array", items=GROUP)
DATES = {name: field(name, "datetime", nullable=True) for name in (
    "lastLogin", "passwordChangedAt", "lastSeenAt")}
FLAGS = {name: field(name, "boolean") for name in (
    "canView", "canUpdateProfile", "canChangeRole", "canChangeGroups", "canChangeSupervisedGroups",
    "canBlock", "canUnblock", "canResetPassword", "canTerminateSessions", "canTransferOwnership")}
AUDIT = obj(action=field("action", options=tuple(EnumOption(code, key) for code, key in AUDIT_ACTION_LABELS.items()),
        placeholder_key="native.employee.unknown_action"),
    result=field("result", "enum", options=tuple(EnumOption(code, f"audit.result_{code.lower()}")
        for code in ("SUCCESS", "DENIED", "FAILED"))), createdAt=field("createdAt", "datetime"))
EMPLOYEE = obj(id=TypeSpec("integer"), membershipId=TypeSpec("integer"),
    email=field("email"), fullName=field("fullName"), phone=field("phone"),
    avatarUrl=field("avatarUrl", nullable=True), role=ROLE, positionTitle=field("positionTitle"),
    groups=replace(GROUPS, title_key="native.employee.groups"),
    supervisedGroups=replace(GROUPS, title_key="native.employee.supervisedGroups"),
    createdAt=field("createdAt", "datetime"), **DATES,
    **{name: field(name, "boolean") for name in (
        "isActive", "isBlocked", "mustChangePassword", "totpRequired", "totpEnabled", "online")},
    workStatus=replace(CURRENT, title_key="native.employee.workStatus"),
    permissions=replace(obj(**FLAGS), title_key="native.employee.permissions"),
    activeSessionCount=field("activeSessionCount", "integer"),
    auditEvents=field("auditEvents", "array", items=AUDIT))
EMPLOYEE = replace(EMPLOYEE, title_key="native.employee.employee", nullable=True)
OUTPUT = obj(employee=EMPLOYEE)
INVITATION = obj(id=TypeSpec("integer"), email=field("email"), fullName=field("fullName"),
    avatarUrl=field("avatarUrl", nullable=True), role=ROLE, positionTitle=field("positionTitle"),
    phone=field("phone"), groups=replace(GROUPS, title_key="native.employee.groups"),
    invitedAt=field("invitedAt", "datetime"), expiresAt=field("expiresAt", "datetime"))
PAGE = replace(page_of(EMPLOYEE), properties=page_of(EMPLOYEE).properties + (
    ("invitations", field("invitations", "array", items=INVITATION)),))
FILTERS = obj(**PAGE_INPUTS, q=field("search"), role=ROLE, group=field("group", "integer"),
    workStatus=replace(STATUS, title_key="native.employee.workStatus"))
EDIT = dict(email=field("email", required=True), fullName=field("fullName", required=True),
    phone=field("phone"), positionTitle=field("positionTitle"), role=ASSIGNABLE,
    groupIds=field("groups", "array", items=TypeSpec("integer")))
