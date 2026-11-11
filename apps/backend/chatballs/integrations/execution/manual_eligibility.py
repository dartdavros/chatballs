"""Read-only manual eligibility; runtime checks still guard every effect."""

from functools import cached_property

from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.models import Conversation
from chatballs.identity.models import EmployeeRole
from chatballs.identity.policy import capabilities_in_any_scope
from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.execution.manual_conditions import (
    known_inputs,
    require_known_conditions,
)
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize
from chatballs.integrations.execution.snapshots import freeze, walk
from chatballs.integrations.scenario_state.grants import ActionGrant


class ManualEligibility:
    def __init__(self, tenant, conversation, *, registry=None, grants=None):
        self.tenant = tenant
        self.conversation = conversation
        self.registry = registry
        self._grants = grants
        self._capability_checks = set()

    @cached_property
    def native_grants(self):
        rows = self._grants if self._grants is not None else ActionGrant.objects.filter(
            organization_id=self.tenant.organization_id, membership=self.tenant.membership, enabled=True)
        return {row.native_key: row for row in rows if row.integration_id is None}

    @cached_property
    def capabilities(self):
        return capabilities_in_any_scope(self.tenant.membership)

    def scenario(self, row, *, parameters=None):
        conversation_id = self.conversation.pk if self.conversation else None
        document = row.definition
        authorize(self.tenant, document, conversation_id, scenario_id=row.pk)
        require_known_conditions(document, self.conversation, parameters=parameters, registry=self.registry)
        frozen = freeze(self.tenant, document, scenario_id=row.public_id, registry=self.registry)
        self.document(document, frozen["graph"], parameters=parameters or {})
        return frozen

    def document(self, document, graph=None, *, scopes=(), parameters=None):
        scopes = (*scopes, document["access"]["scope"])
        parameters = parameters or {}
        for block in walk(document["steps"]):
            if block["kind"] == "action" and block.get("connection") == "chatballs":
                self.native(block, scopes, parameters)
            elif block["kind"] == "call":
                child = graph[str(block["scenario"])]
                data = child["document"]
                if not data["access"]["delegated"]:
                    raise ExecutionDenied("permission")
                authorize(self.tenant, data, self.conversation.pk if self.conversation else None,
                          scenario_id=child["id"], trigger_kind="scenario")
                child_parameters = known_inputs(block["inputs"], self.conversation, parameters, registry=self.registry)
                # Child business guards are evaluated when it is reached: a
                # preceding parent effect may legitimately change their state.
                self.document(data, graph, scopes=scopes, parameters=child_parameters)

    def native(self, block, scopes, parameters):
        action = native_action(block["target"].removeprefix("chatballs:"))
        if action is None:
            self.internal(block, parameters)
            return
        if action.authority != "tenant" or (action.capability and action.capability not in self.capabilities):
            raise ExecutionDenied("permission")
        grant = self.native_grants.get(action.key)
        if self.tenant.membership.role not in {EmployeeRole.OWNER, EmployeeRole.ADMIN} and grant is None:
            raise ExecutionDenied("permission")
        scopes = set(scopes) | ({grant.scope} if grant else set())
        if not scopes <= {"organization", "conversation", "contact"}:
            raise ExecutionDenied("context")
        contextual = bool(scopes & {"conversation", "contact"})
        if action.scope == "organization" and contextual:
            raise ExecutionDenied("context")
        if contextual and (self.conversation is None or (("contact" in scopes or action.scope == "contact") and not self.conversation.contact_id)):
            raise ExecutionDenied("context")
        # Do not resolve unrelated form fields or future step outputs here.
        bindings = {name: value for name, value in block.get("inputs", {}).items() if name in {"conversation_id", "contact_id"}}
        arguments = known_inputs(bindings, self.conversation, parameters, registry=self.registry)
        if contextual and "conversation_id" in arguments and str(arguments["conversation_id"]) != str(self.conversation.pk):
            raise ExecutionDenied("context")
        if contextual and action.scope == "contact" and "contact_id" in arguments and str(arguments["contact_id"]) != str(self.conversation.contact_id):
            raise ExecutionDenied("context")
        if self.conversation is not None and action.capability.startswith("conversations."):
            if action.capability not in self._capability_checks:
                try:
                    require_conversation_action(self.tenant, self.conversation, action.capability)
                except Conversation.DoesNotExist:
                    raise ExecutionDenied("permission") from None
                self._capability_checks.add(action.capability)

    def internal(self, block, parameters):
        # Internal entity links have no employee grant descriptor, but their
        # known endpoint must still exist in this tenant and be active.
        if block["target"] != "chatballs:entity_link.create":
            return
        from chatballs.integrations.models import Integration
        from chatballs.integrations.service_connections.binding import ServiceUnavailable, resolve
        inputs = {key: value for key, value in block.get("inputs", {}).items() if key in {"connection", "entity"}}
        known = known_inputs(inputs, self.conversation, parameters, registry=self.registry)
        if "connection" not in known:
            return
        connection = Integration.objects.filter(pk=known["connection"], organization_id=self.tenant.organization_id).first()
        if connection is None or not connection.is_active or connection.status != "OK":
            raise ExecutionDenied("connection_paused")
        try:
            _, adapter, _ = resolve(connection, self.registry)
        except ServiceUnavailable as error:
            raise ExecutionDenied(error.code) from None
        if "entity" not in known:
            return
        entity = next((item for item in adapter.entities if item.key == known["entity"]), None)
        if entity is None or self.conversation is None:
            raise ExecutionDenied("context")
        if "contact" in entity.native_entities:
            if not self.conversation.contact_id:
                raise ExecutionDenied("context")
        elif "conversation" not in entity.native_entities:
            raise ExecutionDenied("context")
