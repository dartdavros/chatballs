"""Trusted entity exchange bindings, independent of a CRM or transport shape."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EntitySnapshot:
    values: dict
    version: str
    modified_at: datetime
    deleted: bool = False


@dataclass(frozen=True)
class SynchronizationBinding:
    read_operation: str
    read_arguments: Callable[[str], dict]
    snapshot: Callable[[object], EntitySnapshot]
    # Writes must enforce the supplied expected version in the remote system.
    # An adapter without a conditional write must leave this unavailable.
    update_operation: str = ""
    update_arguments: Callable[[str, dict, str, str], dict] | None = None
    delete_operation: str = ""
    delete_arguments: Callable[[str, str, str], dict] | None = None
