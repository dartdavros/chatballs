"""Typed public history fields; provider presentation remains lossless."""

from dataclasses import replace

from chatballs.conversations.models import MessageKind, TranscriptStatus
from chatballs.conversations.system_events import SystemEvent
from chatballs.integrations.action_catalog.schema import BOOLEAN, TEXT, enum, labelled_codes, obj
from chatballs.integrations.adapters.schema import TypeSpec

MESSAGE = replace(obj(id=TypeSpec("integer"), author=enum(("CONTACT", "OPERATOR", "AI", "SYSTEM"), "native.message_author"),
    authorUserId=TypeSpec("integer", nullable=True), authorName=TEXT, authorAvatarUrl=TypeSpec("string", nullable=True),
    kind=enum((*MessageKind.values, "text"), "native.message_kind"), text=TEXT,
    systemEvent=labelled_codes(("", *SystemEvent.values), "native.system_event",
        "native.system_event_unknown"), contentHtml=TEXT, createdAt=TypeSpec("datetime"),
    audioUrl=replace(TEXT, nullable=True), durationSeconds=TypeSpec("integer"), transcript=TEXT,
    transcriptStatus=enum(TranscriptStatus.values, "native.transcript_status"),
    attachmentUrl=replace(TEXT, nullable=True), attachmentName=TEXT, attachmentContentType=TEXT,
    attachmentSize=TypeSpec("integer")), open=True)
WINDOW_INPUTS = {"after": TypeSpec("integer"), "before": TypeSpec("integer"), "limit": TypeSpec("integer")}


def window_of(item, **extra):
    return obj(items=TypeSpec("array", items=item), hasMore=BOOLEAN,
        cursor=TypeSpec("integer", nullable=True), **extra)
