"""Scoped protocol API with content-free errors and ACKs returned after commit."""

from uuid import uuid4

from django.core.exceptions import RequestDataTooBig
from django.http import Http404
from rest_framework.exceptions import (
    AuthenticationFailed,
    ParseError,
    PermissionDenied,
    UnsupportedMediaType,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ai.external_agents import history, ingress
from chatballs.ai.external_agents.auth import authenticated, authorize_session
from chatballs.ai.external_agents.contracts import error_payload, parse, validate
from chatballs.ai.external_agents.delivery import aggregate
from chatballs.ai.external_agents.delivery_models import ExternalAgentDelivery
from chatballs.ai.external_agents.file_uploads import FileConflict
from chatballs.ai.external_agents.formatted_replies import TemplateConflict
from chatballs.ai.external_agents.payloads import utc


class ProtocolView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def handle_exception(self, error):
        if isinstance(error, OSError):
            return Response(error_payload("temporarily_unavailable", str(uuid4())), status=503)
        if isinstance(error, ParseError | UnsupportedMediaType | RequestDataTooBig):
            return Response(error_payload("invalid_request", str(uuid4())), status=400)
        if isinstance(error, AuthenticationFailed | PermissionDenied | Http404 | ingress.Conflict | FileConflict | TemplateConflict | ValueError):
            status = 401 if isinstance(error, AuthenticationFailed) else 403 if isinstance(error, PermissionDenied) else 404 if isinstance(error, Http404) else 409 if isinstance(error, ingress.Conflict | FileConflict | TemplateConflict) else 400
            code = "invalid_credentials" if status == 401 else "resource_not_found" if status == 404 else str(error.get_codes()) if status in (403, 409) else str(error)
            try:
                body = error_payload(code, str(uuid4()))
            except ValueError:
                body = error_payload("invalid_request", str(uuid4()))
            return Response(body, status={"payload_too_large": 413, "unsupported_content": 422}.get(code, status))
        return super().handle_exception(error)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    @staticmethod
    def check_connection(connection, connection_id):
        if connection.pk != connection_id:
            raise Http404


class ResultView(ProtocolView):
    def post(self, request, connection_id, request_id):
        body = parse("result.yaml", "TerminalResult", request.body)
        with authenticated(request.headers.get("Authorization")) as (context, connection):
            self.check_connection(connection, connection_id)
            ack, status = ingress.accept(context, connection, request_id, body)
        return Response(ack, status=status)


class DeliveryView(ProtocolView):
    def get(self, request, connection_id, delivery_id):
        with authenticated(request.headers.get("Authorization")) as (context, connection):
            self.check_connection(connection, connection_id)
            row = ExternalAgentDelivery.objects.select_related("request").filter(
                public_id=delivery_id, request__session__connection=connection,
            ).first()
            if row is None:
                raise Http404
            authorize_session(context, connection, conversation_id=row.request.conversation_id,
                              authorization_id=request.query_params.get("authorizationId"), operation="deliveries")
            if str(row.request.authorization_id) != request.query_params.get("authorizationId"):
                raise Http404
            items = list(row.items.all())
            result = {"version": "1", "deliveryId": str(row.public_id), "state": aggregate(items),
                      "reasonCode": None, "updatedAt": utc(row.updated_at), "items": [
                          {"itemId": str(item.public_id), "messageId": str(item.message_id),
                           "state": item.state, "reasonCode": item.reason_code or None} for item in items]}
            validate("receipts.yaml", "DeliveryStatus", result)
        return Response(result)


class HistoryView(ProtocolView):
    def get(self, request, connection_id, conversation_id):
        with authenticated(request.headers.get("Authorization")) as (context, connection):
            self.check_connection(connection, connection_id)
            result = history.read(context, connection, conversation_id, request.query_params)
            validate("catalogs.yaml", "HistoryPage", result)
        return Response(result)
