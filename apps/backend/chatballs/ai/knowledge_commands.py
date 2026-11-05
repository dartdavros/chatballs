"""Public knowledge commands retain content permissions, indexing and audit."""

from django.core.exceptions import ValidationError
from rest_framework.exceptions import NotFound

from chatballs.ai import knowledge_services as service
from chatballs.ai.indexing import reindex_knowledge
from chatballs.ai.knowledge_api_inputs import knowledge_input
from chatballs.ai.knowledge_import import import_knowledge_documents
from chatballs.ai.knowledge_policy import require_knowledge_create
from chatballs.ai.selectors import writable_knowledge_item_for_employee
from chatballs.ai.serializers import attachment_payload, knowledge_payload
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event


def audit(context, action, knowledge_id, *, request=None, payload=None):
    record_audit_event(action=f"ai.knowledge_{action}", actor=context.membership.user,
        organization=context.organization, object_type="Knowledge", object_id=str(knowledge_id),
        request=request, payload=payload)


def writable(context, knowledge_id):
    return writable_knowledge_item_for_employee(context=context, knowledge_id=knowledge_id)


def create(context, body, *, request=None):
    data = knowledge_input(body)
    require_knowledge_create(context=context)
    knowledge = service.create_knowledge(context=context, data=data)
    knowledge = writable(context, knowledge.id)
    audit(context, "created", knowledge.id, request=request)
    return {"knowledge": knowledge_payload(knowledge)}


def update(context, knowledge_id, body, *, request=None):
    knowledge = writable(context, knowledge_id)
    data = knowledge_input(body, current=knowledge)
    service.update_knowledge(context=context, knowledge=knowledge, data=data)
    knowledge = writable(context, knowledge_id)
    audit(context, "updated", knowledge_id, request=request)
    return {"knowledge": knowledge_payload(knowledge)}


def delete(context, knowledge_id, *, request=None):
    knowledge = writable(context, knowledge_id)
    audit(context, "deleted", knowledge_id, request=request)
    service.delete_knowledge(context=context, knowledge=knowledge)
    return {}


def import_documents(context, documents, *, request=None):
    require_knowledge_create(context=context)
    if not isinstance(documents, list) or not documents:
        raise ValidationError(t("ai.documents_non_empty"))
    result = import_knowledge_documents(context=context, documents=documents).payload()
    audit(context, "imported", "", request=request, payload=result)
    return result


def reindex(context, knowledge_id, *, request=None):
    reindex_knowledge(writable(context, knowledge_id))
    audit(context, "reindexed", knowledge_id, request=request)
    return {"knowledge": knowledge_payload(writable(context, knowledge_id))}


def upload_attachment(context, knowledge_id, upload, *, request=None):
    knowledge = writable(context, knowledge_id)
    if upload is None:
        raise ValidationError(t("ai.file_required"))
    attachment = service.add_attachment(context=context, knowledge=knowledge, upload=upload)
    audit(context, "attachment_added", knowledge_id, request=request)
    return {"attachment": attachment_payload(attachment)}


def remove_attachment(context, knowledge_id, attachment_id, *, request=None):
    knowledge = writable(context, knowledge_id)
    attachment = knowledge.attachments.filter(id=attachment_id).first()
    if attachment is None:
        raise NotFound(t("ai.attachment_not_found"))
    service.delete_attachment(context=context, attachment=attachment)
    audit(context, "attachment_deleted", knowledge_id, request=request)
    return {}
