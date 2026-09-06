"""Пароль первичного доступа сотрудника (дизайн-базлайн v2, кадры E5–E8).

Владелец и администратор задают, как сотрудник получит первый пароль:

* ``mail`` — письмо со ссылкой первого входа на рабочую почту (поведение по
  умолчанию, как было раньше);
* ``show`` — сервер генерирует пароль, возвращает его в ответе ровно один раз и
  сохраняет только хеш. Это нужно, когда почта организации ещё не работает.

В обоих случаях сотруднику ставится ``must_change_password``: свой пароль он
задаёт при первом входе. Выдача и сброс пишутся в журнал действий.
"""

from __future__ import annotations

import secrets

from django.utils import timezone

from chatballs.identity.audit import record_audit_event
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.sessions import revoke_user_sessions

PASSWORD_MODES = ("mail", "show")

# Без похожих друг на друга символов: пароль диктуют голосом и переписывают.
_ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_GROUPS = (3, 4, 4)


def clean_password_mode(value: object) -> str | None:
    """Режим выдачи пароля из тела запроса; None — значение не поддерживается."""
    mode = str(value or "mail")
    return mode if mode in PASSWORD_MODES else None


def generate_initial_password() -> str:
    """Пароль вида «kv7-Rt94-Xmz2»: группы через дефис читаются вслух."""
    return "-".join(
        "".join(secrets.choice(_ALPHABET) for _ in range(size)) for size in _GROUPS
    )


def issue_initial_password(user: HumanUser) -> str:
    """Поставить сотруднику сгенерированный пароль и вернуть его вызывающему.

    В базу уходит только хеш: открытый пароль живёт лишь в этом ответе.
    """
    password = generate_initial_password()
    user.set_password(password)
    user.must_change_password = True
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password", "must_change_password", "password_changed_at"])
    return password


def reset_employee_password(
    *, profile: OrganizationMembership, mode: str, actor, request=None
) -> str | None:
    """Сброс пароля сотрудника. Возвращает пароль только в режиме «показать».

    Активные сессии завершаются в обоих режимах: старый пароль больше не
    действует, и вход по нему из уже открытых окон продолжаться не должен.
    """
    from chatballs.events.services import DomainEvent, enqueue_event
    from chatballs.identity.event_handlers import INITIAL_ACCESS_REQUESTED

    user = profile.user
    password = issue_initial_password(user) if mode == "show" else None
    if mode == "mail":
        user.must_change_password = True
        user.set_unusable_password()
        user.password_changed_at = timezone.now()
        user.save(update_fields=["password", "must_change_password", "password_changed_at"])
    revoked = revoke_user_sessions(user.id)
    record_audit_event(
        action="identity.employee_password_reset",
        actor=getattr(actor, "user", actor),
        organization=profile.organization,
        object_type="HumanUser",
        object_id=str(user.id),
        payload={"mode": mode, "sessionsRevoked": revoked},
        request=request,
    )
    if mode == "mail" and request is not None:
        enqueue_event(
            DomainEvent(
                aggregate_type="HumanUser",
                aggregate_id=str(user.id),
                event_type=INITIAL_ACCESS_REQUESTED,
                payload={"userId": user.id},
                tenant_context=request.tenant_context,
            )
        )
    return password
