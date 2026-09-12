"""Поиск организации там, где tenant-контекста ещё нет.

Роль app видит строку организации только в контексте этой организации
(tenancy/0033). Входы, которые начинаются с внешнего ключа — адрес, публичный
id, слаг, id из outbox-события, — сначала находят id через security-barrier
каталог ``chatballs.organization_directory`` и лишь затем открывают контекст и
читают строку. Так процесс приложения не перечисляет чужие организации.
"""

from __future__ import annotations

from collections.abc import Iterator

from django.db import DEFAULT_DB_ALIAS, connections

from chatballs.identity.models import Organization
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import (
    organization_ids,
    organization_route_by_public_id,
    organization_route_by_slug,
)


def load_organization(organization_id: int) -> Organization | None:
    """Строка организации по id: читается в её собственном контексте."""

    with tenant_atomic(int(organization_id)):
        return Organization.objects.filter(pk=organization_id).first()


def organization_by_public_id(public_id: object) -> Organization | None:
    route = organization_route_by_public_id(str(public_id))
    return load_organization(route.organization_id) if route is not None else None


def organization_by_slug(slug: str) -> Organization | None:
    route = organization_route_by_slug(slug)
    return load_organization(route.organization_id) if route is not None else None


def iter_organizations() -> Iterator[Organization]:
    """Все организации установки по одной, каждая в своём контексте (воркер)."""

    for organization_id in organization_ids():
        organization = load_organization(organization_id)
        if organization is not None:
            yield organization


def reserve_organization_id(*, using: str = DEFAULT_DB_ALIAS) -> int:
    """Выделить id для будущей организации до INSERT.

    Роль app видит строку организации только в её контексте, а INSERT с
    RETURNING обязан вернуть видимую строку. Поэтому мастер первого запуска
    берёт id из последовательности заранее, открывает контекст этого id и уже
    в нём вставляет строку.
    """

    with connections[using].cursor() as cursor:
        cursor.execute("SELECT nextval('identity_organization_id_seq')")
        return int(cursor.fetchone()[0])


def instance_has_organizations(*, using: str = DEFAULT_DB_ALIAS) -> bool:
    """Есть ли в установке хоть одна организация — без tenant-контекста.

    Проверку делает SECURITY DEFINER-функция (tenancy/0032): та же, что держит
    политику «первая организация» мастера первого запуска.
    """

    with connections[using].cursor() as cursor:
        cursor.execute("SELECT chatballs.instance_has_organizations()")
        return bool(cursor.fetchone()[0])
