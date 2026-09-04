from django.core.exceptions import ValidationError
from rest_framework.request import Request

from hub_platform.ai.knowledge_services import KnowledgeInput
from hub_platform.ai.models import Knowledge
from hub_platform.ai.selectors import KnowledgeFilters


def _positive_id(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise ValidationError({field: "Positive integer id required"})
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError({field: "Integer id required"}) from error
    if parsed <= 0:
        raise ValidationError({field: "Positive integer id required"})
    return parsed


def _optional_query_id(value: str | None, field: str) -> int | None:
    return None if value in (None, "") else _positive_id(value, field)


def _category_id(body: dict[str, object], current: Knowledge | None) -> int | None:
    if "categoryId" in body:
        return _positive_id(body["categoryId"], "category")
    if "category" not in body:
        return current.category_id if current else None
    raw = body["category"]
    if isinstance(raw, dict):
        raw = raw.get("id")
    return _positive_id(raw, "category")


def knowledge_input(
    body: dict[str, object], *, current: Knowledge | None = None
) -> KnowledgeInput:
    raw_enabled = body.get("isEnabled", current.is_enabled if current else True)
    if not isinstance(raw_enabled, bool):
        raise ValidationError({"isEnabled": "Boolean required"})
    return KnowledgeInput(
        title=str(body.get("title", current.title if current else "")),
        description=str(
            body.get("description", current.description if current else "")
        ),
        content=str(body.get("content", current.content if current else "")),
        is_enabled=raw_enabled,
        category_id=_category_id(body, current),
    )


def knowledge_filters(request: Request) -> KnowledgeFilters:
    raw_enabled = request.query_params.get("isEnabled")
    if raw_enabled in (None, ""):
        is_enabled = None
    elif raw_enabled.lower() == "true":
        is_enabled = True
    elif raw_enabled.lower() == "false":
        is_enabled = False
    else:
        raise ValidationError({"isEnabled": "Boolean required"})
    return KnowledgeFilters(
        category_id=_optional_query_id(
            request.query_params.get("category"), "category"
        ),
        is_enabled=is_enabled,
        search=request.query_params.get("search", ""),
    )
