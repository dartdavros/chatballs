"""Short scope for the local demo servers to read a published generation."""

from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.fields import UUIDField
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.identity.demo_seed.north_wind.commands import (
    READ_COMMANDS,
    OrderLookup,
    ProductInput,
)
from chatballs.identity.demo_seed.north_wind.delivery import (
    delivery_check_result,
    request_delivery_check,
)
from chatballs.identity.demo_seed.north_wind.local_access import (
    local_demo_enabled,
    read_local_binding,
)
from chatballs.identity.demo_seed.north_wind.loyalty_cases import loyalty_profile
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write, read_state
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.lookup import load_organization

_ORDER_OPERATIONS = frozenset({"order-status", "shipment-status"})
_CARRIER_OPERATIONS = {"delivery-check", "delivery-result", "delivery-health"}
_OPERATIONS = _ORDER_OPERATIONS | _CARRIER_OPERATIONS | {"catalog", "product", "loyalty-profile"}


class DemoLocalReadView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, operation):
        if operation not in _OPERATIONS:
            raise NotFound()
        binding = read_local_binding(request.headers)
        if binding is None:
            raise PermissionDenied()
        if operation in _CARRIER_OPERATIONS and (binding["customer"] != "pavel" or not local_demo_enabled()):
            raise PermissionDenied()
        if operation == "delivery-health":
            return Response({"ready": True})
        organization = load_organization(binding["organization"])
        if organization is None:
            raise NotFound()
        if operation == "loyalty-profile":
            return _loyalty_profile(request, organization, binding)
        carrier = operation in {"delivery-check", "delivery-result"}
        serializer, execute = (OrderLookup, delivery_check_result) if carrier else READ_COMMANDS[operation]
        arguments = dict(request.data)
        if carrier or operation in _ORDER_OPERATIONS:
            arguments["customer"] = binding["customer"]
        payload = serializer(data=arguments)
        payload.is_valid(raise_exception=True)
        reference = str(UUIDField().run_validation(request.headers.get("Idempotency-Key", ""))) if carrier else ""
        try:
            tenant = TenantContext.for_resource(organization)
            if operation == "delivery-check":
                return Response(execute_write(
                    tenant, binding["generation"], request_delivery_check, key=reference,
                    command={**payload.validated_data, "confirmed": True, "reference": reference},
                ))
            state = read_state(tenant, binding["generation"])
            return Response(execute(state, **payload.validated_data, **({"reference": reference} if carrier else {})))
        except ShopError as error:
            return Response({"code": error.code}, status=404)


def _loyalty_profile(request, organization, binding):
    if not local_demo_enabled() or binding["customer"] != "andrey":
        raise PermissionDenied()
    payload = ProductInput(data=request.data)
    payload.is_valid(raise_exception=True)
    try:
        state = read_state(TenantContext.for_resource(organization), binding["generation"])
        return Response(loyalty_profile(state, customer="andrey", product_id=payload.validated_data["product_id"]))
    except ShopError as error:
        return Response({"code": error.code}, status=404)
