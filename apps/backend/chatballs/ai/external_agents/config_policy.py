"""Validate explicit policy selections against the current tenant's resources."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t

POLICY_FIELDS = {
    "policyAccepted": "policy_accepted", "standardFields": "standard_fields",
    "customFields": "custom_fields", "templateIds": "template_ids",
    "proactiveEnabled": "proactive_enabled", "ordinaryTimeout": "ordinary_timeout",
    "longTimeout": "long_timeout", "maximumTimeout": "maximum_timeout",
    "processingMode": "processing_mode",
}


def invalid():
    raise ValidationError(t("external.invalid"))


def policy_values(context, body, binding=None, *, check_template_selection=True):
    from chatballs.ai.models import Skill
    from chatballs.integrations.models import Integration

    defaults = {"policy_accepted": False, "standard_fields": [], "custom_fields": [],
                "template_ids": [], "proactive_enabled": False, "ordinary_timeout": 120,
                "long_timeout": 86400, "maximum_timeout": 86400, "processing_mode": "ordinary"}
    values = {name: body.get(key, getattr(binding, name, default))
              for key, name in POLICY_FIELDS.items() for default in [defaults[name]]}
    if any(type(values[key]) is not bool for key in ("policy_accepted", "proactive_enabled")):
        invalid()
    standard, custom, templates = (values[key] for key in ("standard_fields", "custom_fields", "template_ids"))
    if not isinstance(standard, list) or any(type(item) is not str for item in standard):
        invalid()
    if len(set(standard)) != len(standard) or set(standard) - {"name", "email", "phone"}:
        invalid()
    if not isinstance(templates, list) or any(type(item) is not str for item in templates):
        invalid()
    if len(set(templates)) != len(templates):
        invalid()
    known_templates = [item["id"] for skill in Skill.objects.filter(organization_id=context.organization_id)
                       for item in skill.templates] if templates and check_template_selection else []
    if check_template_selection and any(known_templates.count(identifier) != 1 for identifier in templates):
        invalid()
    if not isinstance(custom, list) or len(custom) > 256:
        invalid()
    seen = set()
    for ref in custom:
        if not isinstance(ref, dict) or set(ref) != {"sourceConnectionId", "fieldId"}:
            invalid()
        source, field = ref["sourceConnectionId"], ref["fieldId"]
        if type(source) is not int or not isinstance(field, str) or not field or (source, field) in seen:
            invalid()
        seen.add((source, field))
        connection = Integration.objects.filter(organization_id=context.organization_id,
                                                pk=source, provider="WEB", is_active=True).first()
        if connection is None or not _has_field(connection, field):
            invalid()
    ordinary, long, maximum = (values[key] for key in ("ordinary_timeout", "long_timeout", "maximum_timeout"))
    if any(type(number) is not int for number in (ordinary, long, maximum)):
        invalid()
    if values["processing_mode"] not in ("ordinary", "long") or not 1 <= ordinary <= long <= maximum <= 2147483647:
        invalid()
    return values


def _has_field(connection, field_id):
    return any(str(field.get("id")) == field_id for field in connection.config.get("fields", [])
               if isinstance(field, dict))
