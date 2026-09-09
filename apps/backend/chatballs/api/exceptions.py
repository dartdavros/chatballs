from typing import Any

from rest_framework.views import exception_handler as drf_exception_handler


def _flatten(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        return "; ".join(_flatten(value) for value in data.values())
    if isinstance(data, list | tuple):
        return "; ".join(_flatten(item) for item in data)
    return str(data)


def api_exception_handler(exc: Exception, context: dict[str, Any]):
    """Normalize every DRF error body to the SPA contract: {"detail": "<text>"}."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if (
        isinstance(data, dict)
        and list(data.keys()) == ["detail"]
        and isinstance(data["detail"], str)
    ):
        return response
    response.data = {"detail": _flatten(data)}
    return response
