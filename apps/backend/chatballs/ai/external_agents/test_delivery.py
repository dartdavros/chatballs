"""A real private panel sink; no customer transport, notifications or queue facts."""


def handoff_test(conversation):
    conversation.control_mode = "HUMAN"
    conversation.expected_responder = "OPERATOR"
    conversation.save(update_fields=["control_mode", "expected_responder"])


def accept_panel(conversation, row, context):
    from chatballs.ai.external_agents.state import applicable
    from chatballs.ai.external_agents.test_scope import active_scope

    active_scope(conversation, row.session.agent)
    if not applicable(row, context):
        raise ValueError("control_changed")
