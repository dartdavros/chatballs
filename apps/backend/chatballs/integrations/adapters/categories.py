"""Explicit, localized operation navigation; independent of remote permissions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationCategory:
    key: str
    title_key: str
