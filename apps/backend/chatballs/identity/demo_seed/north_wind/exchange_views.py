"""Signed visits can read and exchange only the associated customer's order."""

from collections.abc import Mapping

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from chatballs.identity.demo_seed.north_wind.after_sales import exchange_options, request_exchange
from chatballs.identity.demo_seed.north_wind.catalog import pickup_point
from chatballs.identity.demo_seed.north_wind.commands import (
    ExchangeInput,
    ExchangeOptionsInput,
    OrderLookup,
)
from chatballs.identity.demo_seed.north_wind.delivery import shipment_status
from chatballs.identity.demo_seed.north_wind.exchange_widget import issue_exchange_session
from chatballs.identity.demo_seed.north_wind.orders import find_order
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write, read_state
from chatballs.identity.demo_seed.north_wind.storefront_views import _authorize, _error, _response

_INPUTS = {"order": OrderLookup, "options": ExchangeOptionsInput, "submit": ExchangeInput, "chat": OrderLookup}


class DemoExchangeVisitView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, operation):
        if operation not in _INPUTS:
            raise NotFound()
        tenant, binding = _authorize(request)
        customer = binding["customer"]
        if customer not in {"andrey", "andrey-after-purchase"}:
            raise PermissionDenied()
        if not isinstance(request.data, Mapping):
            raise ValidationError({"code": "invalid_request"})
        serializer = _INPUTS[operation](data={**request.data, "customer": customer})
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        generation = binding["generation"]
        try:
            if operation == "submit":
                return _response(execute_write(
                    tenant, generation, request_exchange,
                    key=request.headers.get("Idempotency-Key", ""), command=values,
                ))
            if operation == "chat":
                if customer != "andrey-after-purchase":
                    raise PermissionDenied()
                return _response(issue_exchange_session(tenant, generation, **values))
            state = read_state(tenant, generation)
            if operation == "options":
                return _response(exchange_options(state, **values))
            order = find_order(state, **values)
            exchange = state["exchanges"].get(f'{order["customer"]}:{values["order_number"]}')
            if exchange and "address" not in exchange:
                exchange = {**exchange, "address": pickup_point(state, exchange["store"])["address"]}
            return _response({
                "order": {field: order[field] for field in ("number", "productId", "name", "size", "status")},
                "shipment": shipment_status(state, **values), "exchange": exchange,
            })
        except ShopError as error:
            return _error(error)
