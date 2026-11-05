"""Assistance operation metadata and protected, immutable suggestion text."""

from dataclasses import replace

from chatballs.ai.assistance_models import ReplyAssistanceError, ReplyAssistanceStatus
from chatballs.integrations.action_catalog.schema import TEXT, enum, obj
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

UUID = TypeSpec("string", pattern=r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
ATTEMPT_ID = replace(UUID, title_key="native.assistance_attempt")
SUGGESTION_ID = replace(UUID, title_key="native.assistance_suggestion")
DATE = TypeSpec("datetime", nullable=True)
INTEGER = TypeSpec("integer", nullable=True)
ERROR = TypeSpec("enum", options=(EnumOption("", "native.assistance_error.none"),
    *(EnumOption(value, f"native.assistance_error.{value}") for value in ReplyAssistanceError.values)))
METADATA = dict(id=UUID, status=enum(ReplyAssistanceStatus.values, "native.assistance_status"),
    requestedBy=TypeSpec("integer"), createdAt=TypeSpec("datetime"), startedAt=DATE, completedAt=DATE,
    historyVersion=TEXT, errorCode=ERROR, error=TEXT)
SUGGESTION = obj(**METADATA, attemptId=ATTEMPT_ID, position=TypeSpec("integer"), originalText=TEXT,
    rejectedBy=INTEGER, rejectedAt=DATE, sentMessageId=INTEGER, sentBy=INTEGER, sentAt=DATE)
ATTEMPT = obj(**METADATA, suggestions=TypeSpec("array", items=SUGGESTION))
