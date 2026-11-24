"""The signed wholesale visit is scoped to its own local storefront actions."""

from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from chatballs.identity.demo_seed.north_wind.commands import (
    PartyInput,
    PartyOptionsInput,
    ProposalInput,
)
from chatballs.identity.demo_seed.north_wind.proposal_workflow import (
    proposal_result,
    submit_proposal,
)
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write, read_state
from chatballs.identity.demo_seed.north_wind.storefront_views import _authorize, _error, _response
from chatballs.identity.demo_seed.north_wind.wholesale import party_options, prepare_party_quote


class ResultInput(serializers.Serializer):
    number = serializers.CharField(max_length=32)
    quote_id = serializers.CharField(min_length=36, max_length=36)


_INPUTS = {
    "options": PartyOptionsInput, "quote": PartyInput, "submit": ProposalInput, "status": ResultInput,
}


class DemoProposalVisitView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, operation):
        if operation not in _INPUTS:
            raise NotFound()
        tenant, binding = _authorize(request)
        if binding["customer"] != "school":
            raise PermissionDenied()
        generation = binding["generation"]
        serializer = _INPUTS[operation](data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        key = request.headers.get("Idempotency-Key", "")
        try:
            if operation == "quote":
                return _response(execute_write(
                    tenant, generation, prepare_party_quote, key=key, command=values,
                ))
            if operation == "submit":
                return _response(submit_proposal(tenant, generation, key=key, command=values))
            if operation == "status":
                return _response(proposal_result(tenant, generation, **values))
            state = read_state(tenant, generation)
            return _response(party_options(state, **values))
        except ShopError as error:
            return _error(error)
