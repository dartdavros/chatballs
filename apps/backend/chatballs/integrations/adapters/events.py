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
