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


def _operator_department_code(user: HumanUser | AnonymousUser) -> str | None:
    """Код отдела оператора (EmployeeProfile.department.code) или None.

    SPEC-HUB-0010 §8.1: оператор с доступом к нескольким отделам не поддерживается
    (одиночный FK department). Для полного покрытия требуется DepartmentMembership.
    Сейчас оператор строго в одном отделе: sales ИЛИ support (§10 изоляция inbox).
    """
    if not user.is_authenticated:
        return None
    profile = getattr(user, "employee_profile", None)
    if profile is None or profile.is_blocked or profile.department_id is None:
        return None
    return profile.department.code


def is_sales_operator(user: HumanUser | AnonymousUser) -> bool:
    if is_owner(user):
        return True
    return is_operator(user) and _operator_department_code(user) == "sales"


def is_support_operator(user: HumanUser | AnonymousUser) -> bool:
    if is_owner(user):
        return True
    return is_operator(user) and _operator_department_code(user) == "support"


def can_access_support_workspace(user: HumanUser | AnonymousUser) -> bool:
    # OWNER видит всё; OPERATOR — только если назначен в отдел поддержки.
    return is_owner(user) or (
        is_operator(user) and _operator_department_code(user) == "support"
    )
