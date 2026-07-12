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
    """Compatibility-адаптер этапа 1 (ADR-HUB-0027): «оператор» — это рабочая функция,
    которую после миграции выполняет обычный сотрудник (EMPLOYEE) в своём отделе.
    Операционная авторизация остаётся прежней до этапа 3 (capability-модель)."""
    return get_employee_role(user) == EmployeeRole.EMPLOYEE


def can_access_global_settings(user: HumanUser | AnonymousUser) -> bool:
    return is_owner(user)


def can_access_sales_workspace(user: HumanUser | AnonymousUser) -> bool:
    return get_employee_role(user) in {EmployeeRole.OWNER, EmployeeRole.EMPLOYEE}


def _operator_department_code(user: HumanUser | AnonymousUser) -> str | None:
    """Код основного отдела сотрудника (EmployeeProfile.primary_department.code) или None.

    SPEC-HUB-0010 §8.1: доступ к нескольким отделам не поддерживается (одиночный FK
    primary_department). Для полного покрытия требуется scoped-модель этапа 3.
    Сейчас сотрудник строго в одном отделе: sales ИЛИ support (§10 изоляция inbox).
    """
    if not user.is_authenticated:
        return None
    profile = getattr(user, "employee_profile", None)
    if profile is None or profile.is_blocked or profile.primary_department_id is None:
        return None
    return profile.primary_department.code


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
