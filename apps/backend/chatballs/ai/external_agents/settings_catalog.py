"""Administrative definitions only: no customer values, secrets or cross-tenant fallback."""

from collections import Counter

from chatballs.ai.external_agents.template_models import ExternalAgentTemplateVersion
from chatballs.ai.models import AIAgent, Skill
from chatballs.integrations.models import Integration


def catalog(context):
    organization_id = context.organization_id
    fields = []
    for source in Integration.objects.filter(
        organization_id=organization_id, provider="WEB", is_active=True,
    ).order_by("pk"):
        for field in source.config.get("fields", []):
            if isinstance(field, dict) and field.get("id"):
                fields.append({"sourceConnectionId": source.pk, "sourceName": source.name,
                               "fieldId": str(field["id"]), "label": field.get("label", ""),
                               "type": field.get("type", "string")})
                fields[-1]["options"] = field.get("options", [])
    templates = []
    versions = dict(ExternalAgentTemplateVersion.objects.filter(
        organization_id=organization_id).values_list("template_id", "revision"))
    for skill in Skill.objects.filter(organization_id=organization_id).order_by("pk"):
        for template in skill.templates:
            templates.append({"id": template["id"], "name": template["name"],
                              "skillId": str(skill.public_id),
                              "revision": versions.get(template["id"]),
                              "purpose": template.get("purpose", "")})
    counts = Counter(item["id"] for item in templates)
    return {"agents": [{"id": agent.pk, "channelId": agent.channel_id,
                         "name": agent.channel.name}
                        for agent in AIAgent.objects.filter(organization_id=organization_id)
                        .select_related("channel").order_by("pk")],
            "sources": list(Integration.objects.filter(organization_id=organization_id, provider="WEB", is_active=True)
                            .order_by("pk").values("id", "name")),
            "customFields": fields,
            "templates": [item for item in templates if counts[item["id"]] == 1 and item["revision"]]}


def template_preview(context, template_id):
    from django.http import Http404

    from chatballs.ai.external_agents.config_access import owner
    from chatballs.ai.external_agents.config_policy import invalid
    from chatballs.ai.skill_templates.engine import render_template
    from chatballs.ai.skill_templates.errors import TemplateError
    from chatballs.i18n import customer_language
    from chatballs.tenancy.database import tenant_atomic

    with tenant_atomic(context):
        organization = owner(context)
        matches = [template for skill in Skill.objects.filter(organization_id=context.organization_id)
                   for template in skill.templates if template["id"] == str(template_id)]
        if len(matches) != 1:
            raise Http404
        template = matches[0]
        if not template.get("examples"):
            invalid()
        try:
            rendered = render_template(template, template["examples"][0], language=customer_language(organization))
        except TemplateError:
            invalid()
        return {"formatVersion": 1, "text": rendered["text"], "presentation": rendered["presentation"]}
