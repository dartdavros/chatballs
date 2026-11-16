"""A scoped guard for autonomous work; assistance and analysis remain independent."""

from contextlib import contextmanager
from contextvars import ContextVar

from chatballs.ai.provider.base import ProviderRejected

_guard = ContextVar("autonomous_execution_guard", default=None)
_handoff = ContextVar("autonomous_transport_handoff", default=None)


def check_execution():
    guard = _guard.get()
    if guard is not None and not guard():
        raise ProviderRejected("autonomous turn cancelled")


@contextmanager
def execution_guard(check, *, handoff=None):
    token = _guard.set(check)
    handoff_token = _handoff.set(handoff)
    try:
        check_execution()
        yield
    finally:
        _handoff.reset(handoff_token)
        _guard.reset(token)


@contextmanager
def transport_handoff():
    """Only the actual transport handoff serializes with a control transition."""
    factory = _handoff.get()
    if factory is None:
        check_execution()
        yield
    else:
        with factory():
            yield
