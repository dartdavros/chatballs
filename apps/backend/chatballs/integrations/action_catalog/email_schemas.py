"""Queued mail operations and factual attempts, with no delivery promise."""

from dataclasses import replace

from chatballs.conversations.email_attempt_models import EmailAttemptError, EmailAttemptState
from chatballs.integrations.action_catalog.schema import BOOLEAN, TEXT, enum, obj
from chatballs.integrations.adapters.schema import TypeSpec

INTEGER = TypeSpec("integer")
DATE = TypeSpec("datetime")
ATTEMPT = obj(id=INTEGER, number=replace(INTEGER, title_key="native.email_attempt_number"), state=enum(EmailAttemptState.values, "native.email_state"),
    initiatedById=INTEGER, initiatedByName=TEXT,
    errorCode=enum(EmailAttemptError.values, "native.email_error"), errorMessage=TEXT,
    createdAt=DATE, startedAt=replace(DATE, nullable=True, title_key="native.email_started_at"), finishedAt=replace(DATE, nullable=True))
OPERATION = obj(id=INTEGER, messageId=INTEGER, threadId=INTEGER, mailMessageId=TEXT,
    connectionId=INTEGER, recipient=TEXT, subject=TEXT, senderAddress=replace(TEXT, nullable=True),
    mailboxName=replace(TEXT, nullable=True), initiatedById=INTEGER, createdAt=DATE,
    retryAllowed=BOOLEAN, deliveryConfirmed=BOOLEAN, attempts=TypeSpec("array", items=ATTEMPT, title_key="native.email_attempts"))
OPTIONS = obj(addresses=TypeSpec("array", items=TEXT),
    mailboxes=TypeSpec("array", items=obj(id=INTEGER, name=TEXT, address=TEXT)))
OPERATIONS = obj(items=TypeSpec("array", items=OPERATION), nextCursor=replace(INTEGER, nullable=True))
