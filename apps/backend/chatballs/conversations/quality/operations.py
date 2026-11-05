"""Quality application services shared by HTTP and scenario actions."""

from rest_framework.exceptions import NotFound, ValidationError

from chatballs.conversations.history_selectors import customer_visible_messages
from chatballs.conversations.models import Message
from chatballs.conversations.support_filters import parse_filters
from chatballs.i18n import customer_language, t
from chatballs.tenancy.database import tenant_atomic

from .access import require_quality_conversation
from .corrections import append_quality_correction
from .criteria import configure_quality, require_management
from .models import QualitySettings
from .presentation import job_payload
from .queue import launch_quality
from .selectors import job_for_context, quality_jobs, report_jobs
from .settings_presentation import criteria_value_literals, scale_catalog, suggested_criteria


def validate_body(data, allowed, required=()):
    if not isinstance(data, dict) or set(data) - set(allowed) or set(required) - set(data):
        raise ValidationError(t("quality.request_invalid"))
    return data


def settings(context):
    require_management(context)
    row = QualitySettings.objects.filter(organization_id=context.organization_id).first()
    version = row.current_version if row else None
    return {"enabled": row.enabled if row else False,
            "criteriaVersion": version.version if version else None,
            "nextCriteriaVersion": version.version + 1 if version else 1,
            "criteriaCreatedAt": version.created_at.isoformat() if version else None,
            "criteria": version.criteria if version else [], "scales": scale_catalog(),
            "suggestedCriteria": suggested_criteria(customer_language(context.organization)) if version is None else None,
            "criteriaValueLiterals": criteria_value_literals(version.criteria) if version else {}}


def change_settings(context, data):
    data = validate_body(data, ("enabled", "criteria"), ("enabled",))
    configure_quality(context=context, enabled=data["enabled"], criteria=data.get("criteria"))
    return settings(context)


def launch(context, conversation_id, data):
    data = validate_body(data, ("operationId", "repeat"), ("operationId",))
    with tenant_atomic(context):
        job = launch_quality(context=context, conversation_id=conversation_id,
            operation_id=data["operationId"], repeat=data.get("repeat", False))
        return job_payload(job, context)


def conversation_jobs(context, conversation_id):
    require_quality_conversation(context, conversation_id)
    return {"jobs": [job_payload(job, context) for job in quality_jobs(context).filter(conversation_id=conversation_id)]}


def job(context, job_id):
    return job_payload(job_for_context(context, job_id), context)


def report(context, parameters):
    filters = parse_filters(parameters)
    return {"period": filters.payload(), "jobs": [job_payload(job, context) for job in report_jobs(context, filters)]}


def correct(context, job_id, data):
    data = validate_body(data, ("expectedRevision", "criterionCode", "value", "scaleIndex", "reason"),
        ("expectedRevision", "criterionCode", "reason"))
    if ("value" in data) == ("scaleIndex" in data):
        raise ValidationError(t("quality.request_invalid"))
    row = job_for_context(context, job_id)
    result = getattr(row, "result", None)
    if result is None:
        raise ValidationError(t("quality.result_invalid"))
    append_quality_correction(context=context, result_id=result.pk,
        expected_revision=data["expectedRevision"], criterion_code=data["criterionCode"],
        value=data.get("value"), scale_index=data.get("scaleIndex"), reason=data["reason"])
    return job_payload(row, context)


def evidence(context, job_id, message_id):
    row = job_for_context(context, job_id)
    result = getattr(row, "result", None)
    ids = {pk for item in result.data.get("conclusions", []) for pk in item["messageIds"]} if result else set()
    message = customer_visible_messages(Message.objects.filter(
        pk=message_id, organization_id=context.organization_id,
        conversation_id=row.conversation_id, system_event="", author_type__in=("CONTACT", "OPERATOR", "AI"),
    )).first() if message_id in ids else None
    if message is None:
        raise NotFound(t("quality.not_found"))
    return {"messageId": message.pk, "conversationId": message.conversation_id,
            "authorType": message.author_type, "createdAt": message.created_at.isoformat(),
            "text": message.text, "contentHtml": message.content_html, "transcript": message.transcript}
