from __future__ import annotations

import re
import uuid
from collections.abc import Callable

from django.http import Http404, HttpRequest, HttpResponse
from django.urls import Resolver404, resolve

from chatballs.events.context import get_correlation_id
from chatballs.identity.models import Organization, OrganizationMembership
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic


class TenantContextMiddleware:
    """Resolve an authenticated membership from the organization URL UUID.

    По умолчанию весь вызов view проходит в одной транзакции: RLS-контекст
    ставится через ``SET LOCAL`` и живёт ровно столько же, сколько она. Это
    удобно и даёт запросу атомарность, но у этого есть цена — пока идёт
    обращение наружу (провайдер AI, мессенджер), запрос держит соединение из
    пула, а пул на процесс небольшой.

    Поэтому вьюха, которая ходит наружу и умеет разложить работу на «прочитать
    — сходить — записать», может выставить ``tenant_manages_own_transaction`` и
    открывать ``tenant_atomic`` сама, вокруг обращений к базе. Забытый блок не
    опасен: без транзакции RLS-настройка пуста и строки просто не видны —
    ошибка проявится сразу, а не утечкой в чужую организацию.
    """

    route_kwarg = "organization_public_id"
    route_pattern = re.compile(
        r"^/api/v1/organizations/"
        r"(?P<public_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})(?:/|$)"
    )

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        match = self.route_pattern.match(request.path_info)
        if match is None:
            return self.get_response(request)
        if not request.user.is_authenticated or not request.user.is_active:
            raise Http404
        try:
            public_id = uuid.UUID(match.group("public_id"))
            organization = Organization.objects.get(public_id=public_id)
        except (ValueError, Organization.DoesNotExist) as error:
            raise Http404 from error

        with tenant_atomic(organization.pk):
            try:
                membership = (
                    OrganizationMembership.objects.select_related(
                        "organization", "user"
                    )
                    .get(
                        organization=organization,
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
            if not self._view_manages_own_transaction(request):
                return self.get_response(request)
        return self.get_response(request)

    @staticmethod
    def _view_manages_own_transaction(request: HttpRequest) -> bool:
        try:
            view = resolve(request.path_info).func
        except Resolver404:
            return False
        # DRF кладёт класс вьюхи в атрибут cls у результата as_view().
        return bool(getattr(getattr(view, "cls", None), "tenant_manages_own_transaction", False))

    def process_view(self, request: HttpRequest, view_func, view_args, view_kwargs):
        public_id = view_kwargs.get(self.route_kwarg)
        if public_id is None:
            return None
        if getattr(request, "tenant_context", None) is None:
            raise Http404
        if request.tenant_context.organization.public_id != public_id:
            raise Http404
        del view_kwargs[self.route_kwarg]
        return None
