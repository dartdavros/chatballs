"""Product reply failures, independent of an HTTP request or runner."""

from dataclasses import dataclass

from chatballs.i18n import t


@dataclass(frozen=True)
class ReplyProblem:
    payload: dict
    status: int


def problem(key, status=400):
    return ReplyProblem({"detail": t(key)}, status)
