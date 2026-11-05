"""Personal language preference and its existing organization fallback."""
from django.utils import translation

from chatballs.i18n import t
from chatballs.i18n.languages import normalize_language, resolve_language
from chatballs.identity.audit import record_audit_event
from chatballs.identity.auth.common import _user_payload
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.identity.instance_settings import default_language
from chatballs.identity.models import OrganizationMembership
from chatballs.integrations.action_catalog.authority import current_user
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import membership_routes_for_user


def update(user, body, *, request=None):
    user = current_user(user)
    raw = str(body.get("language", "")).strip()
    language = normalize_language(raw)
    if raw and not language:
        return CommandOutcome({"detail": t("settings.language_unsupported")}, status=400)
    user.ui_language = language
    user.save(update_fields=["ui_language"])
    record_audit_event(
        action="identity.profile_language_changed",
        actor=user,
        object_type="HumanUser",
        object_id=str(user.id),
        request=request,
    )
    # Ответ уже на новом языке: интерфейс перерисуется по нему сразу, не
    # дожидаясь следующего запроса.
    resolved = resolve_language(
        user_language=language,
        organization_language=organization_language(user, getattr(request, "tenant_context", None)),
        instance_language=default_language(),
        accept_language=request.headers.get("Accept-Language") if request else "",
    )
    with translation.override(resolved):
        return CommandOutcome({"authenticated": True, "user": _user_payload(user)})


def organization_language(user, context=None) -> str:
    """Язык организации запроса, если он у этого запроса вообще есть.

    Профиль открывается вне организации, поэтому tenant_context здесь обычно
    пуст: тогда язык берётся из единственного членства, а при нескольких —
    из того, что старше, чтобы ответ не зависел от порядка выборки.
    """

    if context is not None:
        return context.organization.language or ""
    # Членства роли app без контекста не видны: сначала каталог входа, затем
    # каждое членство читается в контексте своей организации — как в
    # identity.auth.common._user_payload.
    oldest: tuple[object, int, str] | None = None
    for route in membership_routes_for_user(user.id):
        with tenant_atomic(route.organization_id):
            membership = (
                OrganizationMembership.objects.select_related("organization")
                .filter(id=route.resource_id, user=user, blocked_at__isnull=True)
                .first()
            )
        if membership is None:
            continue
        key = (membership.created_at, membership.id, membership.organization.language or "")
        if oldest is None or key[:2] < oldest[:2]:
            oldest = key
    return oldest[2] if oldest is not None else ""
