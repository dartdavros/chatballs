from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.db import connections

from hub_platform.identity.crypto import decrypt_secret


@dataclass(frozen=True, slots=True)
class IngressRoute:
    organization_id: int
    resource_id: int | str


@dataclass(frozen=True, slots=True)
class SupportIngressRoute(IngressRoute):
    support_secret: str


def _rows(query: str, parameters: list[Any]) -> list[tuple]:
    alias = "default" if settings.TESTING else "platform"
    with connections[alias].cursor() as cursor:
        cursor.execute(query, parameters)
        return list(cursor.fetchall())


def _unique_route(view: str, lookup_key: str) -> IngressRoute | None:
    rows = _rows(
        f"SELECT organization_id, resource_id FROM custocrm.{view} "
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
            "SELECT organization_id, resource_id FROM custocrm.membership_directory "
            "WHERE user_id = %s AND blocked_at IS NULL ORDER BY organization_id, resource_id",
            [user_id],
        )
    ]


def user_requires_totp(user_id: int) -> bool:
    return bool(
        _rows(
            "SELECT 1 FROM custocrm.membership_directory "
            "WHERE user_id = %s AND blocked_at IS NULL AND totp_required LIMIT 1",
            [user_id],
        )
    )


def attachment_route(public_id: str) -> IngressRoute | None:
    return _unique_route("attachment_directory", public_id)


def call_invite_route(token_hash: str) -> IngressRoute | None:
    return _unique_route("call_invite_directory", token_hash)


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


def support_channel_routes(channel_code: str) -> list[SupportIngressRoute]:
    return [
        SupportIngressRoute(
            organization_id=int(row[0]),
            resource_id=int(row[1]),
            support_secret=decrypt_secret(row[2]),
        )
        for row in _rows(
            "SELECT organization_id, resource_id, support_token_secret "
            "FROM custocrm.support_channel_directory WHERE lookup_key = %s "
            "ORDER BY resource_id",
            [channel_code],
        )
    ]


def support_conversation_route(
    conversation_id: int,
    snapshot_id: int,
) -> IngressRoute | None:
    rows = _rows(
        "SELECT organization_id, resource_id FROM custocrm.support_conversation_directory "
        "WHERE resource_id = %s AND snapshot_id = %s LIMIT 2",
        [conversation_id, snapshot_id],
    )
    if len(rows) != 1:
        return None
    return IngressRoute(organization_id=int(rows[0][0]), resource_id=int(rows[0][1]))
