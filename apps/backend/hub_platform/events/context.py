from contextvars import ContextVar
from uuid import uuid4

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def ensure_correlation_id(value: str | None = None) -> str:
    correlation_id = value or str(uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str:
    return correlation_id_var.get() or ensure_correlation_id()
