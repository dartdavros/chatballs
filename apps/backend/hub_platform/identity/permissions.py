from django.contrib.auth.models import AnonymousUser

from hub_platform.identity.models import EmployeeRole, HumanUser


def get_employee_role(user: HumanUser | AnonymousUser) -> str | None:
    if not user.is_authenticated:
        return None
    profile = getattr(user, "employee_profile", None)
    if profile is None or profile.is_blocked:
        return None
    return profile.role


def is_owner(user: HumanUser | AnonymousUser) -> bool:
    return get_employee_role(user) == EmployeeRole.OWNER


def is_operator(user: HumanUser | AnonymousUser) -> bool:
    return get_employee_role(user) == EmployeeRole.OPERATOR


def can_access_global_settings(user: HumanUser | AnonymousUser) -> bool:
    return is_owner(user)


def can_access_sales_workspace(user: HumanUser | AnonymousUser) -> bool:
    return get_employee_role(user) in {EmployeeRole.OWNER, EmployeeRole.OPERATOR}
