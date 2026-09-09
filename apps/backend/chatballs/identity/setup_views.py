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
from chatballs.identity.auth.common import _user_payload
from chatballs.identity.setup import (
    SetupAlreadyCompleted,
    SetupInput,
    complete_setup,
    instance_needs_setup,
)


# Функция, а не константа: язык запроса решается на каждый запрос заново.
def setup_closed() -> dict[str, str]:
    return {"detail": t("identity.setup_already_done")}


def _validation_response(error: ValidationError) -> Response:
    if hasattr(error, "message_dict"):
        errors = {
            key: messages[0] if isinstance(messages, list) else str(messages)
            for key, messages in error.message_dict.items()
        }
        # validate_password кладёт сообщения без ключа поля.
        if "__all__" in errors:
            errors["password"] = " ".join(error.message_dict["__all__"])
            del errors["__all__"]
        detail = next(iter(errors.values()), "Проверьте заполненные поля")
        return Response({"detail": detail, "errors": errors}, status=400)
    message = " ".join(error.messages)
    return Response({"detail": message, "errors": {"password": message}}, status=400)


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
            result = complete_setup(
                SetupInput(
                    organization_name=str(body.get("organizationName", "")),
                    full_name=str(body.get("fullName", "")),
                    email=str(body.get("email", "")),
                    password=str(body.get("password", "")),
                    install_demo=bool(body.get("installDemo", False)),
                ),
                public_host=request.get_host(),
                public_scheme=request.scheme,
            )
        except SetupAlreadyCompleted:
            return Response(setup_closed(), status=409)
        except ValidationError as error:
            return _validation_response(error)
        owner = result.owner
        owner.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, owner)
        return Response({"authenticated": True, "user": _user_payload(owner)}, status=201)
