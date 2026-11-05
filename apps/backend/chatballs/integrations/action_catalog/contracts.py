"""Executable native contracts, independent of HTTP and service connections."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from chatballs.integrations.adapters.contracts import (
    DEFAULT_LIMITS,
    OperationDescriptor,
    OperationResult,
)
from chatballs.tenancy.context import TenantContext


class NativeOperationRejected(ValueError):
    """A confirmed rejection, distinct from an ambiguous external outcome."""


class NativeAccessDenied(PermissionError):
    """A resource check rejected the call before its domain effect."""


@dataclass(frozen=True)
class NativeContext:
    tenant: TenantContext
    effect_key: str
    run_id: str
    step_path: str
    open_file: Callable | None = None
    store_file: Callable | None = None
    scope: str = "organization"
    conversation_id: int | None = None
    contact_id: str | None = None
    max_file_bytes: int = DEFAULT_LIMITS.max_file_bytes

    def require_conversation(self, conversation_id):
        """Check the canonical resource, including targets addressed by token/UUID."""
        if self.scope != "organization" and str(conversation_id) != str(self.conversation_id):
            raise NativeAccessDenied("context")

    def require_contact(self, contact_id):
        if self.scope != "organization" and (self.contact_id is None or str(contact_id) != self.contact_id):
            raise NativeAccessDenied("context")


@dataclass(frozen=True)
class APIEntry:
    route: str
    method: str
    handler: str
    surface: str = "app"


@dataclass(frozen=True)
class NativeAction:
    operation: OperationDescriptor
    execute: Callable[[NativeContext, dict[str, Any]], OperationResult]
    capability: str
    scope: str
    entries: tuple[APIEntry, ...] = ()
    # local: effect and checkpoint share a transaction. io: a send marker
    # precedes the call; recovery must never assume a database rollback undid I/O.
    execution: str = "local"
    contract_version: int = 1
    authority: str = "tenant"

    @property
    def key(self):
        return self.operation.key
