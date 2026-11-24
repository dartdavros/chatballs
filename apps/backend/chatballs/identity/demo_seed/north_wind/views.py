from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.identity.demo_seed.north_wind.commands import READ_COMMANDS, WRITE_COMMANDS
from chatballs.identity.demo_seed.north_wind.delivery_events import update_shipment
from chatballs.identity.demo_seed.north_wind.proposal_workflow import submit_proposal
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write, read_state
from chatballs.identity.demo_seed.north_wind.support_media import receive_demo_photo


class SupportPhotoInput(serializers.Serializer):
    dialog = serializers.ChoiceField(choices=("team", "exchange"))


class DemoShopCRMView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "company.manage"}

    def get(self, request, generation, reference, **kwargs):
        try:
            item = read_state(request.tenant_context, generation)["crm"][reference]
        except (KeyError, ShopError) as error:
            raise NotFound() from error
        return Response({"number": reference, **item}, headers={"Cache-Control": "no-store"})


class DemoShopView(APIView):
    """Local mock-shop HTTP route for an authenticated demo administrator."""

    permission_classes = [HasCapability]
    required_capabilities = {"POST": "company.manage"}

    def post(self, request, generation, operation, **kwargs):
        if operation == "support-photo":
            command = SupportPhotoInput, receive_demo_photo
        else:
            command = READ_COMMANDS.get(operation) or WRITE_COMMANDS.get(operation)
        if command is None:
            raise NotFound()
        serializer, execute = command
        payload = serializer(data=request.data)
        payload.is_valid(raise_exception=True)
        context = request.tenant_context
        try:
            if operation in READ_COMMANDS:
                result = execute(read_state(context, generation), **payload.validated_data)
            elif operation == "delivery":
                result = update_shipment(
                    context, generation, key=request.headers.get("Idempotency-Key", ""),
                    command=payload.validated_data,
                )
            elif operation == "support-photo":
                result = execute(
                    context, generation, key=request.headers.get("Idempotency-Key", ""), **payload.validated_data,
                )
            elif operation == "proposal":
                value = submit_proposal(context, generation, key=request.headers.get("Idempotency-Key", ""),
                                        command=payload.validated_data)
                result = value["proposal"]
            else:
                result = execute_write(
                    context, generation, execute,
                    key=request.headers.get("Idempotency-Key", ""),
                    command=payload.validated_data,
                )
        except ShopError as error:
            status = 404 if error.code == "demo_generation_unavailable" else 409
            return Response({"code": error.code}, status=status)
        return Response(result)
