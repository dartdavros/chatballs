from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from hub_platform.calls.errors import CallAccessDenied, CallConflict, CallTokenError
from hub_platform.calls.models import CallSession
from hub_platform.calls.permissions import ensure_call_access
from hub_platform.calls.serializers import call_payload, public_invite_payload
from hub_platform.calls.services import (
    create_call_request,
    issue_staff_access_token,
    resolve_invite,
)
from hub_platform.conversations.models import Conversation
from hub_platform.identity.audit import record_audit_event


def _call_queryset():
    return CallSession.objects.select_related(
        "conversation",
        "conversation__channel",
        "initiated_by",
        "delivery_connection",
    ).prefetch_related("participants")


def _token_response(payload: dict, *, status: int = 200) -> Response:
    response = Response(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


class CallCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            created = create_call_request(conversation_id=conversation_id, initiator=request.user)
        except Conversation.DoesNotExist:
            return Response({"detail": "Диалог не найден"}, status=404)
        except CallAccessDenied as error:
            return Response({"detail": str(error)}, status=403)
        except CallConflict as error:
            return Response({"detail": str(error)}, status=409)

        call = _call_queryset().get(id=created.call_session.id)
        record_audit_event(
            action="calls.requested",
            actor=request.user,
            organization=call.organization,
            object_type="CallSession",
            object_id=str(call.id),
            payload={"conversation_id": call.conversation_id},
            request=request,
        )
        return _token_response(
            {"call": call_payload(call), "staffAccessToken": created.staff_access_token},
            status=201,
        )


class CallDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, call_session_id) -> Response:
        try:
            call = _call_queryset().get(id=call_session_id)
        except CallSession.DoesNotExist:
            return Response({"detail": "Звонок не найден"}, status=404)
        try:
            ensure_call_access(user=request.user, call_session=call)
        except CallAccessDenied as error:
            return Response({"detail": str(error)}, status=403)
        return Response({"call": call_payload(call)})


class StaffAccessTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, call_session_id) -> Response:
        try:
            call = _call_queryset().get(id=call_session_id)
            token = issue_staff_access_token(call_session=call, user=request.user)
        except CallSession.DoesNotExist:
            return Response({"detail": "Звонок не найден"}, status=404)
        except CallAccessDenied as error:
            return Response({"detail": str(error)}, status=403)
        except CallConflict as error:
            return Response({"detail": str(error)}, status=409)
        return _token_response({"accessToken": token})


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
            return Response({"detail": "Недействительное или истёкшее приглашение"}, status=404)
        return _token_response(
            {
                "call": public_invite_payload(
                    resolved.invite.call_session,
                    resolved.invite.expires_at,
                ),
                "accessToken": resolved.customer_access_token,
            }
        )
