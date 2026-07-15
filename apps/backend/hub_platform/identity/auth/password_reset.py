from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from hub_platform.events.services import DomainEvent, enqueue_event
from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.event_handlers import PASSWORD_RESET_REQUESTED
from hub_platform.identity.models import AuditResult, HumanUser


def _user_from_reset_link(uid: str, token: str) -> HumanUser | None:
    try:
        user = HumanUser.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError, HumanUser.DoesNotExist):
        return None
    if not user.is_active or not default_token_generator.check_token(user, token):
        return None
    return user


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request: Request) -> Response:
        email = HumanUser.objects.normalize_email(str(request.data.get("email", "")).strip())
        if email:
            user = HumanUser.objects.filter(email__iexact=email, is_active=True).first()
            if user is not None:
                enqueue_event(
                    DomainEvent(
                        aggregate_type="HumanUser",
                        aggregate_id=str(user.id),
                        event_type=PASSWORD_RESET_REQUESTED,
                        payload={"userId": user.id},
                    )
                )
                record_audit_event(
                    action="identity.password_reset_requested",
                    actor=user,
                    request=request,
                )
            else:
                record_audit_event(
                    action="identity.password_reset_requested",
                    result=AuditResult.DENIED,
                    object_type="email",
                    object_id=email,
                    request=request,
                )
        # Ответ не зависит от наличия аккаунта — защита от перебора адресов.
        return Response({"ok": True})


class PasswordResetValidateView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        user = _user_from_reset_link(request.query_params.get("uid", ""), request.query_params.get("token", ""))
        return Response({"valid": user is not None})


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request: Request) -> Response:
        body = request.data
        user = _user_from_reset_link(str(body.get("uid", "")), str(body.get("token", "")))
        if user is None:
            record_audit_event(action="identity.password_reset_failed", result=AuditResult.DENIED, request=request)
            return Response({"detail": "Ссылка недействительна или истекла"}, status=400)

        new_password = str(body.get("newPassword", ""))
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as error:
            return Response({"detail": " ".join(error.messages)}, status=400)

        user.set_password(new_password)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        record_audit_event(
            action="identity.password_reset_completed",
            actor=user,
            request=request,
        )
        return Response({"ok": True})
