from chatballs.i18n import t
from chatballs.identity.models import (
    POSITION_TITLE_MAX_LENGTH,
    EmployeeGroup,
    EmployeeRole,
)

ASSIGNABLE_ROLES = {EmployeeRole.ADMIN, EmployeeRole.SUPERVISOR, EmployeeRole.EMPLOYEE}


def clean_position_title(raw: object) -> tuple[str, str | None]:
    value = str(raw or "").strip()
    if not value:
        return "", t("admin.position_title_required")
    if len(value) > POSITION_TITLE_MAX_LENGTH:
        return value, t("admin.position_title_too_long", limit=POSITION_TITLE_MAX_LENGTH)
    return value, None


def resolve_groups(organization, raw: object) -> tuple[list[EmployeeGroup] | None, str | None]:
    """Валидирует список id групп из запроса; None на входе — «не менять»."""
    if raw is None:
        return None, None
    if not isinstance(raw, list) or any(type(item) is not int for item in raw):
        return None, t("admin.group_ids_invalid")
    requested = list(dict.fromkeys(raw))
    groups = list(EmployeeGroup.objects.filter(organization=organization, id__in=requested))
    if len(groups) != len(requested):
        return None, t("admin.group_not_found")
    return groups, None
