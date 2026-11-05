"""Observe the source transport outcome without changing delivery or retry."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class DeliveryObservation:
    attempted: bool = False
    accepted: bool = True


_observation = ContextVar("public_reply_delivery", default=None)


@contextmanager
def capture_delivery():
    observation = DeliveryObservation()
    token = _observation.set(observation)
    try:
        yield observation
    finally:
        _observation.reset(token)


def observed_send(sender, *args, **kwargs):
    observation = _observation.get()
    if observation is not None:
        observation.attempted = True
    accepted = sender(*args, **kwargs)
    if observation is not None:
        observation.accepted = observation.accepted and bool(accepted)
    return accepted
