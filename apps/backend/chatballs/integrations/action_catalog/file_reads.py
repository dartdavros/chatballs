"""Binary reads and exports use source selectors and normal quota-backed files."""

import io
import json
from dataclasses import replace
from functools import partial

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import PermissionDenied, ValidationError

from chatballs.conversations import contact_services
from chatballs.conversations.diagnostic_export import conversation_diagnostic
from chatballs.conversations.media_queries import visible_message
from chatballs.conversations.models import MessageKind
from chatballs.conversations.support_export import export_csv, export_xlsx
from chatballs.conversations.support_filters import parse_filters
from chatballs.conversations.support_report import calculate_support_report
from chatballs.conversations.transports.base import guess_content_type
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied
from chatballs.integrations.action_catalog.report_schemas import FILTERS
from chatballs.integrations.action_catalog.resources import audit, conversation
from chatballs.integrations.action_catalog.schema import CONVERSATION_ID, IDENTIFIER, action, obj
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.tenancy.database import tenant_atomic

FILE_RESULT = obj(file=TypeSpec("file"))


def stored(context, name, content_type, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    if len(content) > context.max_file_bytes:
        raise NativeAccessDenied("arguments")
    reference = context.store_file(name, content_type, io.BytesIO(content), len(content))
    return OperationResult(ResultState.COMPLETED, {"file": {"fileId": reference.file_id}}, files=(reference,))


def stream_result(context, stream, name, content_type):
    try:
        return stored(context, name, content_type, stream.read(context.max_file_bytes + 1))
    finally:
        stream.close()


def media(context, values, *, audio=False):
    with tenant_atomic(context.tenant):
        try:
            message = visible_message(context.tenant, values["message_id"])
            context.require_conversation(message.conversation_id)
            field = message.audio if audio else message.attachment
            if not field or not audio and message.kind != MessageKind.FILE:
                raise NativeAccessDenied("context")
            name = "voice-message" if audio else message.attachment_name or "file"
            content_type = (message.audio_content_type if audio else message.attachment_content_type or guess_content_type(name))
            stream = field.open("rb")
        except ObjectDoesNotExist:
            raise NativeAccessDenied("context") from None
    return stream_result(context, stream, name, content_type or "application/octet-stream")


def avatar(context, values):
    context.require_contact(values["contact_id"])
    with tenant_atomic(context.tenant):
        try:
            contact = contact_services.avatar(context.tenant, values["contact_id"])
            stream = contact.avatar.open("rb")
        except (ObjectDoesNotExist, PermissionDenied):
            raise NativeAccessDenied("permission") from None
        content_type = contact.avatar_content_type or "application/octet-stream"
    return stream_result(context, stream, "avatar", content_type)


def diagnostic(context, values):
    context.require_conversation(values["conversation_id"])
    with tenant_atomic(context.tenant):
        try:
            row = conversation(context.tenant, values["conversation_id"], "conversations.diagnostics")
        except ObjectDoesNotExist:
            raise NativeAccessDenied("permission") from None
        payload = conversation_diagnostic(row)
    result = stored(context, f"chatballs-dialog-{row.pk}-diagnostic.json", "application/json",
        json.dumps(payload, ensure_ascii=False, indent=2))
    with tenant_atomic(context.tenant):
        audit(context.tenant, "diagnostic_exported", row)
    return result


def report(context, values, *, exporter, extension, content_type):
    with tenant_atomic(context.tenant):
        try:
            report = calculate_support_report(context=context.tenant, filters=parse_filters(values))
        except (PermissionDenied, ValidationError):
            raise NativeAccessDenied("permission") from None
    return stored(context, f"support-report.{extension}", content_type, exporter(report))


for key, title, fields, handler, route, view, capability, scope in (
    ("contacts.avatar.get", "native.avatar_read", obj(contact_id=replace(IDENTIFIER, title_key="native.fields.contact_id")), avatar,
        "clients/<int:contact_id>/avatar/", "reporting_views.ContactAvatarView", "conversations.view", "contact"),
    ("conversations.diagnostic.get", "native.diagnostic_export", obj(conversation_id=CONVERSATION_ID), diagnostic,
        "<int:conversation_id>/diagnostic/", "diagnostic_views.ConversationDiagnosticView", "conversations.diagnostics", "conversation"),
    ("messages.attachment_file.get", "native.attachment_read", obj(message_id=replace(IDENTIFIER, title_key="native.fields.message_id")), media,
        "messages/<int:message_id>/attachment/", "attachment_views.MessageAttachmentView", "conversations.view", "conversation"),
    ("messages.audio_file.get", "native.audio_read", obj(message_id=replace(IDENTIFIER, title_key="native.fields.message_id")), partial(media, audio=True),
        "messages/<int:message_id>/audio/", "voice_views.MessageAudioView", "conversations.view", "conversation"),
    ("reports.support_csv.get", "native.report_csv", FILTERS,
        partial(report, exporter=export_csv, extension="csv", content_type="text/csv; charset=utf-8"),
        "support-report.csv", "support_views.SupportCSVView", "", "organization"),
    ("reports.support_xlsx.get", "native.report_xlsx", FILTERS,
        partial(report, exporter=export_xlsx, extension="xlsx", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "support-report.xlsx", "support_views.SupportXLSXView", "", "organization"),
):
    action(key=key, title=title, input=fields, output=FILE_RESULT, handler=handler,
        capability=capability, scope=scope, route=f"conversations/{route}",
        view=f"chatballs.conversations.{view}", method="GET", execution="io")
