"""Server-derived editing schemas. No operation is executed to build this catalog."""

from chatballs.ai.models import AIAgent
from chatballs.conversations.models import ConversationLabel
from chatballs.identity.models import EmployeeGroup, OrganizationMembership
from chatballs.integrations.action_catalog.registry import action_schemas
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec
from chatballs.integrations.models import Integration, IntegrationKind, ServiceFile
from chatballs.integrations.scenario_state.definitions import ScenarioDefinition
from chatballs.integrations.scenarios.definition import DefinitionContext
from chatballs.integrations.scenarios.native_events import NATIVE_EVENTS
from chatballs.integrations.scenarios.native_references import entity_link_reference
from chatballs.integrations.scenarios.types import read_type

# Context is intentionally explicit: a browser cannot name arbitrary user,
# organization, connection credentials or Django model fields.
CONTEXT = TypeSpec("object", properties=(
    ("conversation", TypeSpec("object", title_key="scenarios.conversation", properties=(
        ("id", TypeSpec("string", title_key="scenarios.conversation_number")), ("topic", TypeSpec("string", title_key="scenarios.topic")),
        ("channel", TypeSpec("string", title_key="scenarios.channel")),
        ("status", TypeSpec("enum", title_key="scenarios.status", options=tuple(
            EnumOption(value, f"scenarios.status_{value}") for value in ("open", "waiting", "closed", "spam")
        ))),
    ))),
    ("contact", TypeSpec("object", title_key="scenarios.contact", properties=(
        ("id", TypeSpec("string", title_key="scenarios.contact_number")), ("name", TypeSpec("string", title_key="scenarios.contact_name")),
        ("phone", TypeSpec("string", title_key="scenarios.contact_phone")), ("email", TypeSpec("string", title_key="scenarios.contact_email")),
    ))),
))


def definition_context(organization_id: int, *, excluding=None) -> DefinitionContext:
    context = DefinitionContext(context=CONTEXT)
    context.entities = {("chatballs", name): schema for name, schema in CONTEXT.properties}
    context.writable_fields = {("chatballs", "conversation"): {"topic", "status"}, ("chatballs", "contact"): {"name", "phone", "email"}}
    context.staff = set(OrganizationMembership.objects.filter(organization_id=organization_id, blocked_at__isnull=True).values_list("user_id", flat=True))
    context.groups = set(EmployeeGroup.objects.filter(organization_id=organization_id).values_list("id", flat=True))
    context.agents = set(AIAgent.objects.filter(organization_id=organization_id).values_list("id", flat=True))
    context.labels = set(ConversationLabel.objects.filter(organization_id=organization_id).values_list("id", flat=True))
    context.channels = set(Integration.objects.filter(organization_id=organization_id, kind=IntegrationKind.MESSENGER).values_list("id", flat=True))
    registry = default_registry()
    context.events.update({("", key): schema for key, _title, schema in NATIVE_EVENTS})
    for action in action_schemas():
        context.operations["chatballs", f"chatballs:{action.key}"] = (action.input, action.output)
    for connection in Integration.objects.filter(organization_id=organization_id).select_related("service_settings"):
        row = getattr(connection, "service_settings", None)
        if row is None:
            continue
        adapter = registry.adapter(row.adapter_key)
        if adapter is None or adapter.contract_version != row.adapter_version:
            continue
        key = str(connection.pk)
        context.connections.add(key)
        context.entities.update({(key, entity.key): entity.fields for entity in adapter.entities})
        context.writable_fields.update({(key, entity.key): {name for name, _ in entity.fields.properties} for entity in adapter.entities})
        for operation in adapter.operations:
            context.operations[key, f"service:{operation.key}"] = (operation.input, operation.output)
        for event in adapter.events:
            context.events[key, event.key] = event.payload
    for scenario in ScenarioDefinition.objects.filter(organization_id=organization_id).exclude(public_id=excluding):
        document = scenario.definition
        context.scenarios[str(scenario.public_id)] = (read_type(document["parameters"]), read_type(document["results"]))
    context.files = {str(pk) for pk in ServiceFile.objects.filter(organization_id=organization_id).values_list("public_id", flat=True)}
    return context


def connection_ids(document):
    found = set()
    from chatballs.integrations.scenarios.definition import child_lists
    def add(value):
        if isinstance(value, str | int) and str(value).isdecimal():
            found.add(int(value))
    def visit(steps):
        for step in steps:
            add(step.get("connection"))
            ref = entity_link_reference(step)
            if ref:
                add(ref[0])
            conditions(step.get("condition", {}))
            for _key, children in child_lists(step):
                visit(children)
    def conditions(group):
        if not isinstance(group, dict) or not isinstance(group.get("items", []), list):
            return
        for condition in group.get("items", []):
            if isinstance(condition, dict) and condition.get("kind") in {"no_link", "has_link"}:
                add(condition.get("connection"))
    visit(document["steps"])
    conditions(document["conditions"])
    for trigger in document["triggers"]:
        add(trigger.get("connection"))
    for pair in document["synchronization"]:
        for side in ("left", "right"):
            if isinstance(pair.get(side), dict):
                add(pair[side].get("connection"))
    return found
