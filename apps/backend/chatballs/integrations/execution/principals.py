"""Nested execution intersects snapshot/current policies of every ancestor."""

from chatballs.integrations.execution.permissions import ExecutionDenied, authorize


def authorize_chain(tenant, run):
    kind = run.definition.get("triggerKind", "staff")
    if kind in {"chatballs", "service", "schedule", "api"}:
        from chatballs.integrations.execution.automation import check
        if run.scenario_id is None:
            raise ExecutionDenied("scenario_disabled")
        check(tenant, run.definition["document"], run.scenario_id, run.definition["trigger"])
        check(tenant, run.scenario.definition, run.scenario_id, run.definition["trigger"], current=True)
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
        from chatballs.integrations.execution.permissions import context_values
        from chatballs.integrations.scenarios.values import RunValues
        require_conditions(parent.definition["document"], conversation, parent.definition["parameters"], values=RunValues(
            parameters=parent.definition["parameters"], context=context_values(conversation), event=parent.definition.get("event", {})))
    return authorize(tenant, run.definition["document"], run.conversation_id,
                     scenario_id=run.scenario_id, trigger_kind="scenario" if run.parent_id else kind)
