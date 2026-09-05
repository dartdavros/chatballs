"""Принудительный выбор соединения БД для блока кода.

Runtime backend-app держит два соединения: ``default`` (роль app) и
``platform`` (роль platform, права на создание организаций — SPEC-HUB-0021).
Обычные запросы идут в ``default``; операции уровня инстанса (мастер первого
запуска) выполняются целиком на ``platform`` через ``use_database("platform")``,
чтобы транзакция и RLS-контекст жили на одном соединении.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_forced_alias: ContextVar[str | None] = ContextVar("hub_forced_db_alias", default=None)


@contextmanager
def use_database(alias: str) -> Iterator[None]:
    token = _forced_alias.set(alias)
    try:
        yield
    finally:
        _forced_alias.reset(token)


def forced_database() -> str | None:
    return _forced_alias.get()


class ForcedAliasRouter:
    """Django database router: внутри ``use_database`` все запросы идут в алиас."""

    def db_for_read(self, model, **hints):  # noqa: ANN001, ARG002
        return _forced_alias.get()

    def db_for_write(self, model, **hints):  # noqa: ANN001, ARG002
        return _forced_alias.get()

    def allow_relation(self, obj1, obj2, **hints):  # noqa: ANN001, ARG002
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):  # noqa: ANN001, ARG002
        return None
