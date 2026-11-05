"""Personal session commands require the caller's actual, still-valid session."""

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, load_backend
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from rest_framework.exceptions import PermissionDenied

from chatballs.identity.audit import record_audit_event
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.identity.sessions import list_user_sessions, revoke_user_sessions
from chatballs.integrations.action_catalog.authority import current_user


def require_session(user, session_key):
    user = current_user(user)
    session = Session.objects.filter(session_key=session_key, expire_date__gt=timezone.now()).first()
    data = session.get_decoded() if session else {}
    backend = data.get(BACKEND_SESSION_KEY)
    if str(data.get(SESSION_KEY)) != str(user.pk) or backend not in settings.AUTHENTICATION_BACKENDS:
        raise PermissionDenied()
    if load_backend(backend).get_user(user.pk) is None:
        raise PermissionDenied()
    hashes = [user.get_session_auth_hash(), *user.get_session_auth_fallback_hash()]
    if not any(constant_time_compare(data.get(HASH_SESSION_KEY, ""), value) for value in hashes):
        raise PermissionDenied()
    return user


def read(user, session_key):
    user = require_session(user, session_key)
    return CommandOutcome({"items": list_user_sessions(user.pk, session_key)})


def revoke_others(user, session_key, *, request=None):
    user = require_session(user, session_key)
    revoked = revoke_user_sessions(user.pk, except_session_key=session_key)
    record_audit_event(action="identity.profile_sessions_revoked", actor=user,
        payload={"revoked": revoked}, request=request)
    return CommandOutcome({"revoked": revoked})
