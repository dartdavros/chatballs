"""Freeze the complete permitted context before any external-agent HTTP."""

from chatballs.ai.external_agents.canonical import digest
from chatballs.ai.external_agents.content_constraints import constraints
from chatballs.ai.external_agents.contracts import validate
from chatballs.ai.external_agents.custom_fields import snapshot as field_snapshot
from chatballs.ai.external_agents.file_access import issue
from chatballs.ai.external_agents.history_payloads import cursor, page
from chatballs.ai.external_agents.json_payloads import size
from chatballs.ai.external_agents.payloads import open_payload, seal, utc
from chatballs.ai.external_agents.public_messages import history_messages, trigger_payload
from chatballs.conversations.models import Contact
from chatballs.i18n import DEFAULT_LANGUAGE, customer_language
from chatballs.identity.instance_settings import public_base_url


def fit_window(snapshot, history, row):
    window = snapshot["context"]["history"]
    while size(snapshot) > 262144:
        if not window["messages"]:
            raise ValueError("payload_too_large")
        window["messages"] = window["messages"][1:]
        window["truncated"] = True
        window["nextCursor"] = cursor(row, len(history) - len(window["messages"]))


def prepare(row):
    if row.snapshot_ciphertext:
        return
    binding = row.session.agent.external_binding
    trigger = row.trigger
    if not row.conversation.is_test and (row.conversation.connection_id is None or row.conversation.contact_id is None):
        raise ValueError("channel_restricted")
    # Native site/manual updates lock this same contact. Keep standard and
    # custom values in one consistent read while the immutable request is built.
    if row.conversation.is_test:
        from chatballs.ai.external_agents.test_context import customer

        customer_data = customer(row, binding)
    else:
        contact = Contact.objects.select_for_update().get(
            pk=row.conversation.contact_id, organization_id=row.conversation.organization_id)
        customer_data = {"id": str(contact.pk),
                         "fields": {key: getattr(contact, key) for key in sorted(binding.standard_fields)},
                         "customFields": field_snapshot(binding, contact)}
    seed = open_payload(row.seed_ciphertext)
    trigger_data = trigger_payload(trigger, seed, row)
    history = history_messages(row)
    # Pagination cannot split or silently truncate a public message. Verify that
    # every item is readable in its exact single-item page before exporting work.
    if any(size(page(row, [item], position)) > 262144
           for position, item in enumerate(history)):
        raise ValueError("payload_too_large")
    base = public_base_url().rstrip("/")
    if not base.startswith("https://"):
        raise ValueError("channel_restricted")
    route = f"{base}/api/v1/external-agent/connections/{row.session.connection_id}"
    language = row.session.agent.answer_language
    language_mode = {"MIRROR": "mirror", "ORGANIZATION": "organization"}.get(language, "fixed")
    snapshot = {
        "version": "1", "requestId": str(row.public_id), "createdAt": utc(trigger.created_at),
        "deadlineAt": utc(row.deadline_at),
        "agent": {"id": str(row.session.agent_id), "externalAgentId": binding.external_agent_id},
        "conversation": {"id": str(row.conversation_id),
                         "externalSessionId": row.session.external_session_id or None,
                         "authorizationId": str(row.authorization_id), "turnSequence": row.sequence},
        "trigger": trigger_data,
        "context": {
            "history": {"mode": "window", "snapshotCursor": cursor(row), "truncated": len(history) > 20,
                        "messages": history[-20:], "historyUrl": route + f"/conversations/{row.conversation_id}/history/",
                        "nextCursor": cursor(row, len(history) - 20) if len(history) > 20 else None},
            "customer": customer_data,
            "dataPolicy": {"revision": binding.policy_version, "mode": "agreed_original",
                           "fields": sorted(binding.standard_fields), "customFields": []},
            "language": {"mode": language_mode,
                         "organization": customer_language(row.conversation.organization) or DEFAULT_LANGUAGE,
                         "requested": language if language_mode == "fixed" else None},
        },
        "permissions": {"reply": True, "handoff": True, "proactive": False},
        "deliveryConstraints": constraints(row),
        "callbacks": {"resultUrl": route + f"/requests/{row.public_id}/result/"},
    }
    snapshot["context"]["dataPolicy"]["customFields"] = snapshot["context"]["customer"]["customFields"]["scope"]
    validate("request.yaml", "AgentRequest", snapshot)
    fit_window(snapshot, history, row)
    issue(row, trigger_data["attachments"] + [item["content"] for item in snapshot["context"]["history"]["messages"]])
    row.snapshot_ciphertext, row.history_ciphertext = seal(snapshot), seal(history)
    row.snapshot_digest = digest(row.session.connection.deduplication_key,
                                 operation="createGoCoStackRequest", route=[], body=snapshot)
    row.save(update_fields=["snapshot_ciphertext", "history_ciphertext", "snapshot_digest"])
