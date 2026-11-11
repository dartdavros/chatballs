"""Optional, tenant-owned presentation metadata; never an access grant."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t

UNSET_CATEGORY_PATH = object()
MAX_CATEGORY_DEPTH = 3
MAX_CATEGORY_LENGTH = 80


def category_path(value):
    def invalid():
        raise ValidationError({"categoryPath": t("scenarios.category_invalid")})

    if not isinstance(value, list) or len(value) > MAX_CATEGORY_DEPTH:
        invalid()
    result = []
    for part in value:
        if not isinstance(part, str):
            invalid()
        name = part.strip()
        if (
            not name or len(name) > MAX_CATEGORY_LENGTH or "/" in name
            or any(ord(char) < 32 or ord(char) == 127 for char in part)
        ):
            invalid()
        result.append(name)
    return result
