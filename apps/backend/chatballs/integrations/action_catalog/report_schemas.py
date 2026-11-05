"""Named time and historical dimension filters shared with quality reports."""

from dataclasses import replace

from chatballs.conversations.domain_event_models import ConversationEventTransport
from chatballs.integrations.action_catalog.schema import TEXT, enum, obj, required
from chatballs.integrations.adapters.schema import TypeSpec

INTEGER = TypeSpec("integer")
FILTER_FIELDS = {"from": required(TypeSpec("datetime")), "to": required(TypeSpec("datetime")),
    "timezone": required(TEXT), "employee": INTEGER, "group": INTEGER, "connection": INTEGER,
    "transport": enum(ConversationEventTransport.values, "native.report_transport")}
FILTERS = obj(**FILTER_FIELDS)
PERIOD = obj(**{name: replace(spec, required=False, nullable=name in {"employee", "group", "connection", "transport"})
    for name, spec in FILTER_FIELDS.items()})
