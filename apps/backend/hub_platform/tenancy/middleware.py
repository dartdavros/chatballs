from __future__ import annotations

from collections.abc import Callable

from django.http import Http404, HttpRequest, HttpResponse

from hub_platform.events.context import get_correlation_id
from hub_platform.identity.models import OrganizationMembership
from hub_platform.tenancy.context import TenantContext


class TenantContextMiddleware:
    """Resolve an authenticated membership from the organization URL UUID."""

    route_kwarg = "organization_public_id"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_view(self, request: HttpRequest, view_func, view_args, view_kwargs):
        public_id = view_kwargs.get(self.route_kwarg)
        if public_id is None:
            return None
        if not request.user.is_authenticated or not request.user.is_active:
            raise Http404
        try:
            membership = (
                OrganizationMembership.objects.select_related(
                    "organization", "user", "primary_department"
                )
                .get(
                    organization__public_id=public_id,
                    user=request.user,
                    blocked_at__isnull=True,
                )
            )
        except OrganizationMembership.DoesNotExist as error:
            raise Http404 from error
        if membership.totp_required and not request.user.totp_enabled:
            raise Http404
        request.tenant_context = TenantContext.for_membership(
            membership,
            correlation_id=get_correlation_id(),
        )
        del view_kwargs[self.route_kwarg]
        return None
