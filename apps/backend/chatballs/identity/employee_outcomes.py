"""Domain outcomes keep denial audit durable without coupling commands to HTTP."""

from dataclasses import dataclass

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import AuditResult


@dataclass(frozen=True)
class EmployeeOutcome:
    data: dict
    problem: str = ""


def rejected(detail, problem="invalid"):
    return EmployeeOutcome({"detail": detail}, problem)


def denied(context, target, action, *, request=None):
    record_audit_event(action="identity.employee_privileged_action_denied",
        actor=context.actor_user, organization=context.organization, object_type="HumanUser",
        object_id=str(target.user_id) if target else "", result=AuditResult.DENIED,
        payload={"action": action, "targetRole": target.role if target else None}, request=request)
    return rejected(t("admin.action_not_allowed_for_employee"), "forbidden")
