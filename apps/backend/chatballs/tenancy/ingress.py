from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import connections


@dataclass(frozen=True, slots=True)
class IngressRoute:
    organization_id: int
    resource_id: int | str


def _rows(query: str, parameters: list[Any]) -> list[tuple]:
    # Каталоги — security-barrier вьюхи, на них есть SELECT у роли app
    # (tenancy/0032): чтение идёт по основному соединению процесса.
    with connections["default"].cursor() as cursor:
        cursor.execute(query, parameters)
        return list(cursor.fetchall())


def _unique_route(view: str, lookup_key: str) -> IngressRoute | None:
    rows = _rows(
        f"SELECT organization_id, resource_id FROM chatballs.{view} "
        "WHERE lookup_key = %s ORDER BY resource_id LIMIT 2",
        [lookup_key],
    )
    if len(rows) != 1:
        return None
    return IngressRoute(organization_id=int(rows[0][0]), resource_id=rows[0][1])


def membership_routes_for_user(user_id: int) -> list[IngressRoute]:
    return [
        IngressRoute(organization_id=int(row[0]), resource_id=int(row[1]))
        for row in _rows(
            "SELECT organization_id, resource_id FROM chatballs.membership_directory "
            "WHERE user_id = %s AND blocked_at IS NULL ORDER BY organization_id, resource_id",
            [user_id],
        )
    ]


def user_requires_totp(user_id: int) -> bool:
    return bool(
        _rows(
            "SELECT 1 FROM chatballs.membership_directory "
            "WHERE user_id = %s AND blocked_at IS NULL AND totp_required LIMIT 1",
            [user_id],
        )
    )


def attachment_route(public_id: str) -> IngressRoute | None:
    return _unique_route("attachment_directory", public_id)


def portal_article_file_route(public_id: str) -> IngressRoute | None:
    return _unique_route("portal_article_file_directory", public_id)


def call_invite_route(token_hash: str) -> IngressRoute | None:
    return _unique_route("call_invite_directory", token_hash)


def invitation_route(token_hash: str) -> IngressRoute | None:
    """Приглашение в организацию по хэшу токена из письма (/join).

    Ссылка открывается без контекста — токен и есть единственный ключ. Каталог
    (tenancy/0035) отдаёт организацию, а само приглашение читается уже в ней.
    """

    return _unique_route("invitation_directory", token_hash)


def call_session_route(call_session_id: str) -> IngressRoute | None:
    return _unique_route("call_session_directory", call_session_id)


def web_session_route(token_hash: str) -> IngressRoute | None:
    return _unique_route("web_session_directory", token_hash)


def web_channel_route(channel_code: str) -> IngressRoute | None:
    return _unique_route("web_channel_directory", channel_code)


def web_widget_route(public_key: str) -> IngressRoute | None:
    return _unique_route("web_widget_directory", public_key)


def support_portal_route(hostname: str) -> IngressRoute | None:
    return _unique_route("support_portal_directory", hostname.strip().lower().rstrip("."))


# Каталог организаций: id по публичному id или слагу, публичный id по id и
# список всех id. Роль app видит строку организации только в её контексте
# (tenancy/0033), а сюда приходят до того, как контекст открыт.
def organization_route_by_public_id(public_id: str) -> IngressRoute | None:
    rows = _rows(
        "SELECT organization_id, public_id FROM chatballs.organization_directory "
        "WHERE public_id = %s::uuid",
        [public_id],
    )
    if len(rows) != 1:
        return None
    return IngressRoute(organization_id=int(rows[0][0]), resource_id=str(rows[0][1]))


def organization_route_by_slug(slug: str) -> IngressRoute | None:
    rows = _rows(
        "SELECT organization_id, slug FROM chatballs.organization_directory WHERE slug = %s",
        [slug],
    )
    if len(rows) != 1:
        return None
    return IngressRoute(organization_id=int(rows[0][0]), resource_id=str(rows[0][1]))


def organization_public_id_of(organization_id: int) -> str | None:
    rows = _rows(
        "SELECT public_id FROM chatballs.organization_directory WHERE organization_id = %s",
        [int(organization_id)],
    )
    return str(rows[0][0]) if rows else None


def organization_ids() -> list[int]:
    return [
        int(row[0])
        for row in _rows(
            "SELECT organization_id FROM chatballs.organization_directory ORDER BY organization_id",
            [],
        )
    ]


