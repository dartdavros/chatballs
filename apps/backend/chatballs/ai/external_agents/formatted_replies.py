"""Explicit native template catalog and one immutable safe renderer snapshot."""

from decimal import Decimal

from rest_framework.exceptions import APIException

from chatballs.ai.external_agents.template_models import ExternalAgentTemplateVersion
from chatballs.ai.models import Skill
from chatballs.ai.skill_templates.engine import render_template
from chatballs.ai.skill_templates.errors import TemplateError
from chatballs.i18n import customer_language


class TemplateConflict(APIException):
    status_code = 409
    default_code = "template_revision_changed"


def selected(binding):
    from chatballs.ai.external_agents.grant_definitions import stale_grants

    if stale_grants(binding)["templateIds"]:
        raise TemplateConflict()
    allowed = set(binding.template_ids)
    result = {}
    for skill in Skill.objects.filter(organization_id=binding.organization_id).order_by("pk"):
        for template in skill.templates:
            if template["id"] in allowed:
                if template["id"] in result:
                    raise TemplateConflict()
                result[template["id"]] = (skill, template)
    if allowed != set(result):
        raise TemplateConflict()
    return result


def revision(binding, identifier):
    return ExternalAgentTemplateVersion.objects.get(
        organization_id=binding.organization_id, template_id=identifier).revision


def catalog(binding):
    return {"version": "1", "items": [
        {"id": identifier, "revision": revision(binding, identifier), "purpose": template["purpose"],
         "dataSchema": template["schema"], "representations": ["text", "html"]}
        for identifier, (skill, template) in selected(binding).items()]}


def prepare(row, content, *, representation):
    binding = row.session.agent.external_binding
    entry = selected(binding).get(content["templateId"])
    if entry is None or revision(binding, content["templateId"]) != content["templateRevision"]:
        raise TemplateConflict()
    skill, template = entry
    try:
        rendered = render_template(template, native_data(content["data"]), language=customer_language(row.conversation.organization))
    except TemplateError as error:
        raise ValueError("invalid_request") from error
    if not rendered["text"].strip():
        raise ValueError("invalid_request")
    return {"text": rendered["text"], "content_html": rendered["contentHtml"],
            "presentation": rendered["presentation"], "format_version": 1,
            "delivery_representation": representation,
            "template_snapshot": {"id": template["id"], "revision": int(content["templateRevision"]),
                                  "skillId": str(skill.public_id), "skillRevision": skill.revision,
                                  "name": template["name"]}}


def current(message, row):
    """Revalidate the version without re-rendering or mutating the saved snapshot."""
    saved = message.template_snapshot
    if not saved:
        return True
    binding = row.session.agent.external_binding
    entry = selected(binding).get(saved.get("id"))
    return bool(entry and revision(binding, saved["id"]) == saved.get("revision"))


def native_data(value):
    """The renderer's bounded numbers must survive conversion without rounding."""
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        converted = float(value)
        if Decimal(str(converted)) != value:
            raise ValueError("invalid_request")
        return converted
    if isinstance(value, dict):
        return {key: native_data(child) for key, child in value.items()}
    if isinstance(value, list):
        return [native_data(child) for child in value]
    return value
