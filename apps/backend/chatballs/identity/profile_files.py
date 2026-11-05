"""Personal avatar operations shared with their original HTTP surface."""

from rest_framework.exceptions import NotFound, ValidationError

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.auth.common import _user_payload
from chatballs.identity.avatars import delete_user_avatar, replace_user_avatar
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.integrations.action_catalog.authority import current_user


def read(user):
    user = current_user(user)
    if not user.avatar:
        raise NotFound(t("profile.photo_not_set"))
    return user.avatar.open("rb"), user.avatar_content_type or "application/octet-stream"


def upload(user, file, *, request=None):
    user = current_user(user)
    if file is None:
        raise ValidationError({"detail": t("profile.choose_photo_file")})
    replace_user_avatar(user, file)
    return _result(user, "identity.avatar_updated", request)


def delete(user, *, request=None):
    user = current_user(user)
    delete_user_avatar(user)
    return _result(user, "identity.avatar_deleted", request)


def _result(user, action, request):
    record_audit_event(action=action, actor=user, object_type="HumanUser", object_id=str(user.pk), request=request)
    return CommandOutcome({"authenticated": True, "user": _user_payload(user)})
