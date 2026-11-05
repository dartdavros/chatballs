"""Trusted global callers; tenant contexts never acquire global authority."""

from dataclasses import dataclass

from rest_framework.exceptions import PermissionDenied

from chatballs.identity.instance_access import can_view_instance_settings, is_instance_admin
from chatballs.identity.models import HumanUser
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied
from chatballs.integrations.adapters.contracts import DEFAULT_LIMITS


@dataclass(frozen=True)
class AuthorityContext:
    """Constructed by trusted server code, never deserialized from a definition."""

    authority: str
    user: object = None
    token: object = None
    session_key: str = ""
    request: object = None
    open_file: object = None
    store_file: object = None
    public_host: str = ""
    public_scheme: str = ""
    max_file_bytes: int = DEFAULT_LIMITS.max_file_bytes


def current_user(user):
    if not isinstance(user, HumanUser) or not user.pk:
        raise PermissionDenied()
    current = HumanUser.objects.filter(pk=user.pk, is_active=True).first()
    if current is None:
        raise PermissionDenied()
    return current


def require_instance(user, *, read=False):
    user = current_user(user)
    if not (can_view_instance_settings(user) if read else is_instance_admin(user)):
        raise PermissionDenied()
    return user


def require_context(context, authority):
    if not isinstance(context, AuthorityContext) or context.authority != authority:
        raise NativeAccessDenied("permission")
    return context


def require_platform(operator, token, capability):
    from chatballs.platform.models import PlatformOperator, PlatformToken

    if not isinstance(operator, PlatformOperator) or not isinstance(token, PlatformToken):
        raise PermissionDenied()
    token = PlatformToken.objects.select_related("operator").filter(
        pk=token.pk, operator_id=operator.pk).first()
    if token is None or token.is_revoked or not token.operator.is_active or capability not in token.capabilities:
        raise PermissionDenied()
    return token.operator
