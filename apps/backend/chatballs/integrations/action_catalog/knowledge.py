"""Knowledge reads and commands use the same application services as HTTP."""

from dataclasses import replace
from functools import partial

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile

from chatballs.ai import knowledge_commands as commands
from chatballs.ai.knowledge_api_inputs import parse_knowledge_filters
from chatballs.ai.knowledge_reads import get_knowledge, list_knowledge
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied
from chatballs.integrations.action_catalog.knowledge_schemas import (
    ATTACHMENT,
    FIELDS,
    FILTERS,
    ID,
    IMPORT,
    IMPORT_RESULT,
    OUTPUT,
    PAGE,
    field,
)
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.tenancy.database import tenant_atomic


def listing(context, values):
    filters = parse_knowledge_filters(values, values.get("agent", ()))
    return OperationResult(ResultState.COMPLETED, list_knowledge(context.tenant, filters, values))


def detail(context, values):
    return OperationResult(ResultState.COMPLETED, get_knowledge(context.tenant, values["knowledge_id"]))


def write(context, values, *, command, body=False, attachment=False, upload=False, documents=False):
    with tenant_atomic(context.tenant):
        # Reject inaccessible targets before opening files or running commands.
        if "knowledge_id" in values:
            try:
                commands.writable(context.tenant, values["knowledge_id"])
            except (ObjectDoesNotExist, PermissionDenied):
                raise NativeAccessDenied("context") from None
        args = [context.tenant]
        if "knowledge_id" in values:
            args.append(values["knowledge_id"])
        if body:
            args.append(values)
        if documents:
            args.append(values["documents"])
        if attachment:
            args.append(values["attachment_id"])
        if upload:
            name, content_type, content = context.open_file(values["file"]["fileId"])
            args.append(SimpleUploadedFile(name, content, content_type))
        result = command(*args)
    return OperationResult(ResultState.COMPLETED, result)


for key, inputs, outputs, handler, method, suffix, view, effect, execution in (
    ("knowledge.get", FILTERS, PAGE, listing, "GET", "", "KnowledgeListCreateView", Effect.READ, "local"),
    ("knowledge.post", obj(**{**FIELDS, "title": required(FIELDS["title"])}), OUTPUT,
        partial(write, command=commands.create, body=True), "POST", "", "KnowledgeListCreateView", Effect.CREATE, "io"),
    ("knowledge.detail.get", obj(knowledge_id=ID), OUTPUT, detail, "GET", "<int:knowledge_id>/", "KnowledgeDetailView", Effect.READ, "local"),
    ("knowledge.detail.patch", obj(knowledge_id=ID, **FIELDS), OUTPUT,
        partial(write, command=commands.update, body=True), "PATCH", "<int:knowledge_id>/", "KnowledgeDetailView", Effect.UPDATE, "io"),
    ("knowledge.detail.delete", obj(knowledge_id=ID), obj(), partial(write, command=commands.delete),
        "DELETE", "<int:knowledge_id>/", "KnowledgeDetailView", Effect.DELETE, "io"),
    ("knowledge.import.post", IMPORT, IMPORT_RESULT, partial(write, command=commands.import_documents, documents=True),
        "POST", "import/", "KnowledgeImportView", Effect.CREATE, "io"),
    ("knowledge.reindex.post", obj(knowledge_id=ID), OUTPUT, partial(write, command=commands.reindex),
        "POST", "<int:knowledge_id>/reindex/", "KnowledgeReindexView", Effect.UPDATE, "io"),
    ("knowledge.attachments.post", obj(knowledge_id=ID, file=field("file", "file", required=True)),
        obj(attachment=replace(ATTACHMENT, title_key="native.knowledge_fields.attachment")), partial(write, command=commands.upload_attachment, upload=True),
        "POST", "<int:knowledge_id>/attachments/", "KnowledgeAttachmentUploadView", Effect.CREATE, "io"),
    ("knowledge.attachment.delete", obj(knowledge_id=ID, attachment_id=field("attachment", "integer", required=True)),
        obj(), partial(write, command=commands.remove_attachment, attachment=True), "DELETE",
        "<int:knowledge_id>/attachments/<int:attachment_id>/", "KnowledgeAttachmentDeleteView", Effect.DELETE, "io"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs, handler=handler,
        capability="ai.view" if method == "GET" else "ai.manage", scope="organization",
        route=f"ai/knowledge/{suffix}", view=f"chatballs.ai.views.{view}", method=method,
        effect=effect, execution=execution)
