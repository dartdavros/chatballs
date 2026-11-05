"""Shared validation and rendering of unsaved skill drafts."""

from chatballs.ai.skill_templates.engine import render_template
from chatballs.ai.skill_templates.errors import TemplateError
from chatballs.ai.skill_templates.schema import validate_data, validate_schema
from chatballs.ai.skills_queries import load, require_manager
from chatballs.ai.skills_validation import configuration
from chatballs.i18n import customer_language


def validate(context, raw, skill_id=None):
    require_manager(context)
    if skill_id is not None:
        load(context, skill_id)
    configuration(raw["configuration"])
    return {"valid": True}


def preview(context, raw, skill_id=None):
    require_manager(context)
    if skill_id is not None:
        load(context, skill_id)
    try:
        values = configuration(raw["configuration"])
    except TemplateError as error:
        templates = raw["configuration"].get("templates", [])
        template = (
            next(
                (
                    item
                    for item in templates
                    if isinstance(item, dict) and item.get("id") == raw["templateId"]
                ),
                None,
            )
            if isinstance(templates, list)
            else None
        )
        if template is not None:
            try:
                schema = validate_schema(template.get("schema"))
            except TemplateError:
                pass
            else:
                try:
                    validate_data(schema, raw["data"], origin="example")
                except TemplateError as data_error:
                    raise TemplateError.combined(
                        error.detail["errors"] + data_error.detail["errors"]
                    ) from None
        raise
    template = next((item for item in values["templates"] if item["id"] == raw["templateId"]), None)
    if template is None:
        raise TemplateError("unknown_field", path="templateId")
    return render_template(
        template, raw["data"], language=customer_language(context.organization), origin="example"
    )


def basis(context):
    require_manager(context)
    from chatballs.ai.skill_templates.order_basis import order_basis

    return {
        "basisId": "orders-v1",
        "configuration": order_basis(language=customer_language(context.organization)),
    }
