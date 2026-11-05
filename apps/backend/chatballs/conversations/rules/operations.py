"""Public rule settings and journal operations, independent of HTTP."""

from rest_framework.exceptions import NotFound, ValidationError

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.rules.catalog import CATALOG, EDITABLE_FIELDS
from chatballs.conversations.rules.journal import execution_payload, journal_for, recipient_names
from chatballs.conversations.rules.presentation import rule_payload
from chatballs.conversations.rules.settings import rules_for, update_rule
from chatballs.i18n import t

API_FIELDS = {api: field for field, api in EDITABLE_FIELDS.items()}


def list_rules(context):
    return {"items": [rule_payload(rule) for rule in rules_for(context.organization_id)]}


def change_rule(context, kind, data):
    if kind not in CATALOG:
        raise NotFound(t("rules.not_found"))
    if not isinstance(data, dict) or not set(data) <= set(API_FIELDS):
        raise ValidationError({"detail": t("rules.settings_invalid")})
    rule = update_rule(context=context, kind=kind,
        changes={API_FIELDS[name]: value for name, value in data.items()})
    return {"rule": rule_payload(rule)}


def rule_journal(context, params):
    page = paginate(journal_for(context, params), params)
    names = recipient_names(context.organization_id, page.items)
    return {**page_payload(page, lambda execution: execution_payload(execution, names)),
        "timezone": context.organization.timezone}
