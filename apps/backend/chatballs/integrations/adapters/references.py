"""Trusted search projections expose choices, never establish identity."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceCandidate:
    id: str
    label: str


@dataclass(frozen=True)
class EntityReferences:
    operation: str
    arguments: Callable[[str], dict]
    candidates: Callable[[object], tuple[ReferenceCandidate, ...]]
    # Trusted local projection only; credentials never leave the backend.
    record_url: Callable[[dict, str], str] | None = None
