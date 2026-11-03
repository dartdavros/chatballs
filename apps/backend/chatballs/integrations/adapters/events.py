"""A trusted ingress verifies original bytes, then returns this typed envelope."""

from dataclasses import dataclass
from datetime import datetime

from chatballs.integrations.adapters.contracts import OperationResult


@dataclass(frozen=True)
class VerifiedEvent:
    event_id: str
    event_key: str
    occurred_at: datetime
    payload: dict
    correlation: str = ""
    sequence: int | None = None
    result: OperationResult | None = None
    causal_chain: tuple[str, ...] = ()
    entity_kind: str = ""
    entity_id: str = ""


@dataclass(frozen=True)
class PollResult:
    events: tuple[VerifiedEvent, ...]
    cursor: str
    retry_after: int = 30
