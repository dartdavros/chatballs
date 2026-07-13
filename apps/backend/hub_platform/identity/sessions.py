from django.contrib.sessions.models import Session


def count_user_sessions(user_id: int) -> int:
    return sum(
        1
        for session in Session.objects.all()
        if str(session.get_decoded().get("_auth_user_id")) == str(user_id)
    )


def revoke_user_sessions(user_id: int, *, except_session_key: str | None = None) -> int:
    """Delete all server-side sessions of a user, optionally keeping one (e.g. the current request)."""
    revoked = 0
    for session in Session.objects.all():
        if except_session_key is not None and session.session_key == except_session_key:
            continue
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(user_id):
            session.delete()
            revoked += 1
    return revoked
