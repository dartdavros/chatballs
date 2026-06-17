from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from hub_platform.events.context import ensure_correlation_id


class CorrelationIdMiddleware:
    header_name = "HTTP_X_CORRELATION_ID"
    response_header = "X-Correlation-Id"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = ensure_correlation_id(request.META.get(self.header_name))
        response = self.get_response(request)
        response[self.response_header] = correlation_id
        return response
