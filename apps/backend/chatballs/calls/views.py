from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from chatballs.calls import operations
from chatballs.calls.errors import CallAccessDenied, CallConflict, CallTokenError
from chatballs.calls.models import CallKind, CallSession
from chatballs.calls.serializers import (
    call_payload,
    ice_servers_payload,
    public_call_state_payload,
    public_invite_payload,
)
from chatballs.calls.services import (
    accept_call_by_access_token,
    call_state_by_access_token,
    decline_call_by_access_token,
    end_call_by_access_token,
    issue_staff_access_token,
    resolve_invite,
)
from chatballs.conversations.models import Conversation
from chatballs.i18n import t

_call_queryset = operations.call_queryset


def _token_response(payload: dict, *, status: int = 200) -> Response:
    response = Response(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


class CallCreateView(APIView):
    permission_classes = [IsAuthenticated]
    required_entitlement = "p2p_calls"

    def post(self, request: Request, conversation_id: int) -> Response:
        if "kind" not in request.data:
            return Response({"detail": t("calls.kind_required")}, status=400)
        kind = str(request.data.get("kind", ""))
        if kind not in CallKind.values:
            return Response({"detail": t("calls.kind_invalid")}, status=400)
        try:
            created, call = operations.create(
                request.tenant_context, conversation_id, kind, request=request,
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        except CallAccessDenied as error:
            return Response({"detail": str(error)}, status=403)
        except CallConflict as error:
            return Response({"detail": str(error)}, status=409)

        return _token_response(
            {
                "call": call_payload(call),
                "staffAccessToken": created.staff_access_token,
                "iceServers": ice_servers_payload(),
            },
            status=201,
        )


class CallDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, call_session_id) -> Response:
        try:
            call = operations.detail(request.tenant_context, call_session_id)
        except CallSession.DoesNotExist:
            return Response({"detail": t("calls.not_found")}, status=404)
        except CallAccessDenied as error:
            return Response({"detail": str(error)}, status=403)
        return Response({"call": call_payload(call)})


class StaffAccessTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, call_session_id) -> Response:
        try:
            call = _call_queryset().get(
                id=call_session_id, organization=request.tenant_context.organization
            )
            token = issue_staff_access_token(context=request.tenant_context, call_session=call)
        except CallSession.DoesNotExist:
            return Response({"detail": t("calls.not_found")}, status=404)
        except CallAccessDenied as error:
            return Response({"detail": str(error)}, status=403)
        except CallConflict as error:
            return Response({"detail": str(error)}, status=409)
        return _token_response({"accessToken": token, "iceServers": ice_servers_payload()})


class CallCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, call_session_id) -> Response:
        try:
            call = operations.cancel(request.tenant_context, call_session_id, request=request)
        except CallSession.DoesNotExist:
            return Response({"detail": t("calls.not_found")}, status=404)
        except CallAccessDenied as error:
            return Response({"detail": str(error)}, status=403)
        except CallConflict as error:
            return Response({"detail": str(error)}, status=409)
        return Response({"call": call_payload(call)})


class ConversationActiveCallView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, conversation_id: int) -> Response:
        try:
            call = operations.active(request.tenant_context, conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        except CallAccessDenied as error:
            return Response({"detail": str(error)}, status=403)
        return Response({"call": call_payload(call) if call else None})


class InviteResolveView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "call_invite"

    def post(self, request: Request) -> Response:
        token = str(request.data.get("token", ""))
        try:
            resolved = resolve_invite(token=token)
        except CallTokenError:
            return Response({"detail": t("calls.invite_invalid")}, status=404)
        return _token_response(
            {
                "call": public_invite_payload(
                    resolved.invite.call_session,
                    resolved.invite.expires_at,
                ),
                "accessToken": resolved.customer_access_token,
                "iceServers": ice_servers_payload(),
            }
        )


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return str(request.data.get("token", "")) if request.method == "POST" else ""


class _CallAccessView(APIView):
    # Клиентские действия по call access token: без Django-сессии, throttle по IP.
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "call_access"


class CallAccessStateView(_CallAccessView):
    def post(self, request: Request) -> Response:
        try:
            call = call_state_by_access_token(token=_bearer_token(request))
        except CallTokenError:
            return Response({"detail": t("calls.token_invalid")}, status=404)
        return _token_response(
            {"call": public_call_state_payload(call), "iceServers": ice_servers_payload()}
        )


class CallAccessAcceptView(_CallAccessView):
    def post(self, request: Request) -> Response:
        try:
            call = accept_call_by_access_token(token=_bearer_token(request))
        except CallTokenError:
            return Response({"detail": t("calls.token_invalid")}, status=404)
        except CallConflict as error:
            return Response({"detail": str(error)}, status=409)
        return _token_response({"call": public_call_state_payload(call)})


class CallAccessDeclineView(_CallAccessView):
    def post(self, request: Request) -> Response:
        try:
            call = decline_call_by_access_token(token=_bearer_token(request))
        except CallTokenError:
            return Response({"detail": t("calls.token_invalid")}, status=404)
        except CallConflict as error:
            return Response({"detail": str(error)}, status=409)
        return _token_response({"call": public_call_state_payload(call)})


class CallAccessEndView(_CallAccessView):
    def post(self, request: Request) -> Response:
        try:
            call = end_call_by_access_token(token=_bearer_token(request))
        except CallTokenError:
            return Response({"detail": t("calls.token_invalid")}, status=404)
        return _token_response({"call": public_call_state_payload(call)})
