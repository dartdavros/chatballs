from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Callable

from django.db import DEFAULT_DB_ALIAS, connections, transaction

from hub_platform.tenancy.context import TenantContext

ORGANIZATION_SETTING = "custocrm.organization_id"


def _organization_id(context_or_id: TenantContext | int) -> int:
    if isinstance(context_or_id, TenantContext):
        return int(context_or_id.organization_id)
    return int(context_or_id)


def set_local_tenant(
    context_or_id: TenantContext | int,
    *,
    using: str = DEFAULT_DB_ALIAS,
) -> None:
    """Set transaction-local RLS context; never mutates pooled session state."""

    connection = connections[using]
    if not connection.in_atomic_block:
        raise RuntimeError("Tenant database context requires transaction.atomic()")
    organization_id = _organization_id(context_or_id)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting(%s, true)", [ORGANIZATION_SETTING])
        current = cursor.fetchone()[0]
        if current not in {None, "", str(organization_id)}:
            raise RuntimeError("Cannot switch tenant inside an active transaction")
        cursor.execute(
            "SELECT set_config(%s, %s, true)",
            [ORGANIZATION_SETTING, str(organization_id)],
        )


@contextmanager
def tenant_atomic(
    context_or_id: TenantContext | int,
    *,
    using: str = DEFAULT_DB_ALIAS,
) -> Iterator[None]:
    connection = connections[using]
    nested = connection.in_atomic_block
    previous = ""
    if nested:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting(%s, true)", [ORGANIZATION_SETTING])
            previous = cursor.fetchone()[0] or ""
    with transaction.atomic(using=using):
        set_local_tenant(context_or_id, using=using)
        yield
    if nested:
        # SET LOCAL survives a released savepoint. Restore the parent scope so
        # a nested tenant operation cannot leak into its technical transaction.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config(%s, %s, true)",
                [ORGANIZATION_SETTING, previous],
            )


def current_tenant_id(*, using: str = DEFAULT_DB_ALIAS) -> int | None:
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT current_setting(%s, true)", [ORGANIZATION_SETTING])
        value = cursor.fetchone()[0]
    return int(value) if value and value.isdigit() else None


def run_tenant_operation(
    context: TenantContext,
    operation: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with tenant_atomic(context):
        return operation(context, *args, **kwargs)
