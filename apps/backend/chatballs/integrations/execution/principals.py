"""Nested execution intersects snapshot/current policies of every ancestor."""

from chatballs.integrations.execution.permissions import ExecutionDenied, authorize


def authorize_chain(tenant, run):
    if run.parent_id:
        current = run.scenario
        if not run.definition["document"]["access"]["delegated"] or current is None or not current.definition["access"]["delegated"]:
            raise ExecutionDenied("permission")
    if run.parent_id:
        parent = run.parent
        if parent.data_cleared_at or parent.cancel_requested_at:
            raise ExecutionDenied("permission")
        _, conversation = authorize_chain(tenant, parent)
        expected_contact = parent.definition.get("context", {}).get("contact", {}).get("id")
        if conversation and expected_contact != (str(conversation.contact_id) if conversation.contact_id else None):
            raise ExecutionDenied("context_changed")
        from chatballs.integrations.execution.conditions import require_conditions
        require_conditions(parent.definition["document"], conversation, parent.definition["parameters"])
    return authorize(tenant, run.definition["document"], run.conversation_id,
                     scenario_id=run.scenario_id, trigger_kind="scenario" if run.parent_id else "staff")
