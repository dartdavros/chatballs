from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.identity.auth.common import _user_payload, validation_response
from chatballs.identity.setup import (
    SetupAlreadyCompleted,
    instance_needs_setup,
)
from chatballs.identity.setup_commands import finish


# Функция, а не константа: язык запроса решается на каждый запрос заново.
def setup_closed() -> dict[str, str]:
    return {"detail": t("identity.setup_already_done")}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SetupStatusView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"needsSetup": instance_needs_setup()})


@method_decorator(csrf_protect, name="dispatch")
class SetupView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request: Request) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        if not instance_needs_setup():
            return Response(setup_closed(), status=409)
        try:
            result = finish(body, public_host=request.get_host(), public_scheme=request.scheme)
        except SetupAlreadyCompleted:
            return Response(setup_closed(), status=409)
        except ValidationError as error:
            return validation_response(error)
        owner = result.owner
        owner.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, owner)
        return Response({"authenticated": True, "user": _user_payload(owner)}, status=201)
