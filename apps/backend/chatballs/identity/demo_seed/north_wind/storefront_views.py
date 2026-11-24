from collections.abc import Mapping

from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.identity.demo_seed.north_wind.appointments import book_fitting, fitting_slots
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS, SIZES
from chatballs.identity.demo_seed.north_wind.commands import (
    FittingInput,
    OrderInput,
    QuoteInput,
    SlotsInput,
)
from chatballs.identity.demo_seed.north_wind.loyalty_site import add_loyalty_proof
from chatballs.identity.demo_seed.north_wind.orders import quote_order
from chatballs.identity.demo_seed.north_wind.prepared_widget import (
    issue_prepared_session,
    locked_dataset,
    prepared_chat_ticket,
)
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write, read_state
from chatballs.identity.demo_seed.north_wind.storefront import (
    prepare_cart,
    storefront_data,
    submit_cart,
)
from chatballs.identity.demo_seed.north_wind.storefront_access import visit_binding
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.lookup import load_organization


class CartInput(serializers.Serializer):
    product_id = serializers.ChoiceField(choices=PRODUCTS)
    size = serializers.ChoiceField(choices=SIZES)


_OPERATIONS = {
    "cart": (CartInput, prepare_cart, True),
    "quote": (QuoteInput, quote_order, False),
    "checkout": (OrderInput, submit_cart, True),
    "fitting-slots": (SlotsInput, fitting_slots, False),
    "fitting": (FittingInput, book_fitting, True),
}


class DemoStorefrontView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, operation):
        if operation != "start":
            raise NotFound()
        tenant, binding = _authorize(request)
        try:
            state = read_state(tenant, binding["generation"])
            storefront = storefront_data(state, customer=binding["customer"])
            route = {"olga": "fitting", "school": "proposal"}.get(binding["customer"])
            prepared = state.get("supportDialogs", {}).get(route, {})
            if prepared.get("widgetKey") == storefront["widgetKey"]:
                storefront["preparedChat"] = {
                    "route": route,
                    "ticket": prepared_chat_ticket(tenant.organization_id, binding["generation"], route,
                                                   storefront["widgetKey"]),
                }
            response = _response(storefront)
            add_loyalty_proof(response, request, binding, storefront)
            return response
        except ShopError as error:
            return _error(error)

    def post(self, request, operation):
        if operation == "executor":
            return self._executor_session(request)
        if operation not in _OPERATIONS:
            raise NotFound()
        tenant, binding = _authorize(request)
        serializer, command, writes = _OPERATIONS[operation]
        if not isinstance(request.data, Mapping):
            raise serializers.ValidationError({"code": "invalid_request"})
        values = {**request.data, "customer": binding["customer"]}
        payload = serializer(data=values)
        payload.is_valid(raise_exception=True)
        arguments = payload.validated_data
        if operation == "cart":
            arguments["customer"] = binding["customer"]
        generation = binding["generation"]
        try:
            if writes:
                value = execute_write(
                    tenant, generation, command,
                    key=request.headers.get("Idempotency-Key", ""),
                    command=arguments,
                )
            else:
                value = command(read_state(tenant, generation), **arguments)
        except ShopError as error:
            return _error(error)
        return _response(value)

    @staticmethod
    def _executor_session(request):
        tenant, binding = _authorize(request)
        if binding.get("executor") is not True or binding["customer"] != "andrey-after-purchase":
            raise PermissionDenied()
        try:
            with tenant_atomic(tenant):
                dataset = locked_dataset(tenant, binding["generation"])
                thread = dataset.shop_state.get("supportDialogs", {}).get("formatted-external", {})
                return _response(issue_prepared_session(dataset, thread))
        except ShopError as error:
            return _error(error)


def _authorize(request):
    binding = visit_binding(request.headers)
    if binding is None:
        raise PermissionDenied()
    organization = load_organization(binding["organization"])
    if organization is None:
        raise NotFound()
    return TenantContext.for_resource(organization), binding


def _response(data, *, status=200):
    return Response(data, status=status, headers={"Cache-Control": "no-store"})


def _error(error):
    status = 404 if error.code == "demo_generation_unavailable" else 409
    return _response({"code": error.code}, status=status)
