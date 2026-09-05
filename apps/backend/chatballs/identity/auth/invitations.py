from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.identity.auth.common import _user_payload
from chatballs.identity.invitation_service import InvitationError, accept_invitation


class InvitationAcceptView(APIView):
    """Accept an OWNER invitation (SPEC-HUB-0021 §8.2).

    Authenticated endpoint: the caller must already have a HumanUser account
    (created through sign-up / password setup). The token is read from the body;
    on success the response returns the standard user payload so the SPA can
    refresh its membership list.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        token = str(request.data.get("token", "")).strip()
        if not token:
            return Response({"detail": "token is required"}, status=400)
        try:
            accept_invitation(token=token, user=request.user)
        except InvitationError as error:
            return Response({"detail": str(error)}, status=400)
        return Response({"user": _user_payload(request.user)})
