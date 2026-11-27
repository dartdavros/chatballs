"""Render an agent's configured greeting from the current widget's saved fields."""

from django.core.exceptions import ValidationError

from chatballs.conversations.models import ContactFieldValue
from chatballs.conversations.site_fields import field_display
from chatballs.conversations.template_variables import TEMPLATE_TOKEN, variable_keys
from chatballs.i18n import customer_language, t
from chatballs.integrations.models import IntegrationProvider
from chatballs.webchat.field_values import BUILTIN_TYPES, validate_field_value
from chatballs.webchat.pre_chat import pre_chat_payload

MAX_GREETING_LENGTH = 4000


def _fields(integration):
    return {
        **{key: {"type": kind, "label": t(f"native.fields.{key}")}
           for key, kind in BUILTIN_TYPES.items()},
        **{row["key"]: row for row in integration.config.get("fields", [])},
    }


def greeting_variables(channel):
    variables = {}
    for connection in channel.connections.all():
        if connection.provider != IntegrationProvider.WEB:
            continue
        form = pre_chat_payload(connection.config)
        for key, definition in _fields(connection).items():
            variable = variables.setdefault(key, {
                "key": key, "token": "{{" + key + "}}", "label": definition.get("label") or key,
                "type": definition["type"], "connectionName": "",
            })
            if key not in BUILTIN_TYPES:
                variable["connectionName"] = ", ".join(filter(None, [variable["connectionName"], connection.name]))
            if form["enabled"] and any(row["key"] == key and row["required"] for row in form["fields"]):
                variable["required"] = True
    return list(variables.values())


def validate_greeting(channel, value):
    if not isinstance(value, str) or len(value) > MAX_GREETING_LENGTH:
        raise ValidationError({"greeting": t("webchat.greeting_invalid", limit=MAX_GREETING_LENGTH)})
    unknown = set(variable_keys(value)) - {row["key"] for row in greeting_variables(channel)}
    if unknown:
        raise ValidationError({"greeting": t("webchat.greeting_unknown_fields", fields=", ".join(sorted(unknown)))})
    return value.strip()


def agent_greeting(channel) -> str:
    agent = getattr(channel, "ai_agent", None)
    return agent.greeting if agent is not None and agent.status != "ARCHIVED" else ""


def render_greeting(session) -> str:
    text = agent_greeting(session.connection.channel)
    if not text:
        return ""
    keys = set(variable_keys(text))
    if not keys:
        return text
    fields = _fields(session.connection)
    language = customer_language(session.organization)
    values = {}
    for row in ContactFieldValue.objects.filter(
        organization_id=session.organization_id, contact_id=session.identity.contact_id,
        integration_id=session.connection_id, key__in=keys & fields.keys(),
    ):
        definition = fields[row.key]
        try:
            value = validate_field_value(row.value, definition)
        except ValueError:
            continue
        if value is not None:
            values[row.key] = field_display(definition, value, language=language).strip()
    if all(values.get(key) for key in keys):
        rendered = TEMPLATE_TOKEN.sub(lambda match: values[match[1].strip()], text)
        if len(rendered) <= MAX_GREETING_LENGTH:
            return rendered
    return session.widget.presentation_config.get("greeting") or t("webchat.default_greeting", language=language)
