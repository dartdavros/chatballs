"""Personal profile commands act only on the authenticated global user."""
from django.db import transaction

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.auth.common import _user_payload
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.identity.models import HumanUser
from chatballs.integrations.action_catalog.authority import current_user


@transaction.atomic
def update(user, body, *, request=None):
    user = current_user(user)
    full_name = str(body.get("fullName", "")).strip()
    email = HumanUser.objects.normalize_email(str(body.get("email", "")).strip())
    if not full_name:
        return CommandOutcome({"detail": t("admin.full_name_required")}, status=400)
    if not email:
        return CommandOutcome({"detail": t("admin.email_required")}, status=400)
    if HumanUser.objects.exclude(id=user.id).filter(email=email).exists():
        return CommandOutcome({"detail": t("admin.email_taken")}, status=400)

    user.full_name = full_name
    user.email = email
    user.save(update_fields=["full_name", "email"])
    record_audit_event(
        action="identity.profile_updated",
        actor=user,
        object_type="HumanUser",
        object_id=str(user.id),
        request=request,
    )
    return CommandOutcome({"authenticated": True, "user": _user_payload(user)})


@transaction.atomic
def appearance(user, body, *, request=None):
    user = current_user(user)
    import re

    from chatballs.identity.models import UiTheme

    theme = str(body.get("theme", user.ui_theme)).strip().upper()
    accent = str(body.get("accent", user.ui_accent)).strip().lower()
    if theme not in UiTheme.values:
        return CommandOutcome({"detail": t("profile.unknown_theme")}, status=400)
    if accent and not re.fullmatch(r"#[0-9a-f]{6}", accent):
        return CommandOutcome({"detail": t("profile.accent_hex")}, status=400)
    user.ui_theme = theme
    user.ui_accent = accent
    user.save(update_fields=["ui_theme", "ui_accent"])
    return CommandOutcome({"authenticated": True, "user": _user_payload(user)})
