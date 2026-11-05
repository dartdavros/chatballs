"""Public knowledge file reads use canonical ingress and native file ownership."""

from chatballs.ai.attachment_reads import open_attachment
from chatballs.ai.models import KnowledgeAttachment
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied
from chatballs.integrations.action_catalog.file_reads import FILE_RESULT, stream_result
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.schema import TypeSpec


def download(context, values):
    try:
        stream, name, content_type = open_attachment(values["public_id"],
            organization_id=context.tenant.organization_id)
    except KnowledgeAttachment.DoesNotExist:
        raise NativeAccessDenied("context") from None
    return stream_result(context, stream, name, content_type or "application/octet-stream")


action(key="knowledge.file.get", title="native.knowledge.file.get",
    input=obj(public_id=TypeSpec("string", required=True, title_key="native.knowledge_fields.publicId")),
    output=FILE_RESULT, handler=download, capability="", scope="organization",
    route="api/v1/ai/files/<uuid:public_id>/", view="chatballs.ai.attachment_views.AttachmentDownloadView",
    method="GET", effect=Effect.READ, execution="io")

