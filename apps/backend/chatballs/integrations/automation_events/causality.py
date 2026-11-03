"""Causal origin for domain hooks, carried only by the current execution."""

from contextlib import contextmanager
from contextvars import ContextVar

chain = ContextVar("integration_causal_chain", default=())


@contextmanager
def origin(value):
    token = chain.set(tuple(value))
    try:
        yield
    finally:
        chain.reset(token)
