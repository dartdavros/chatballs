"""Whitelisted native records use the same contact/lifecycle domain operations."""

import hashlib
import json

from chatballs.conversations.models import Contact, Conversation
from chatballs.identity.policy import require_capability
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.scenario_state.entity_links import IntegrationEntityVersion


def record(tenant, link, *, lock=False):
    kind, identity = link["internal_kind"], link["internal_id"]
    model = Contact if kind == "contact" else Conversation
    rows = model.objects.filter(pk=identity, organization_id=tenant.organization_id)
    row = (rows.select_for_update() if lock else rows).first()
    stamp = IntegrationEntityVersion.objects.filter(organization_id=tenant.organization_id, internal_kind=kind, internal_id=identity).first()
    if kind == "contact" and row and row.merged_into_id:
        raise ExecutionDenied("context_changed")
    from chatballs.conversations.queue import is_waiting
    values = ({name: getattr(row, name) for name in ("name", "phone", "email")} if kind == "contact" else {
        "status": "waiting" if is_waiting(row) else row.lifecycle.lower()}) if row else {}
    digest = hashlib.sha256(json.dumps({"values": values, "deleted": row is None,
        "generation": stamp.version if stamp else None}, sort_keys=True).encode()).hexdigest()
    return {"values": values, "version": digest, "deleted": row is None,
        "modifiedAt": stamp.modified_at.isoformat() if stamp else None}


def apply(tenant, link, expected, patch, *, delete=False):
    current = record(tenant, link, lock=True)
    if current["version"] != expected:
        raise ExecutionDenied("state_changed")
    if link["internal_kind"] == "contact":
        if delete:
            # Contact deletion is not a public product operation. Never invent it.
            raise ExecutionDenied("operation_unavailable")
        contact = Contact.objects.get(pk=link["internal_id"], organization_id=tenant.organization_id)
        if not require_capability(tenant.membership, "customers.manage", contact):
            raise ExecutionDenied("permission")
        if set(patch) - {"name", "phone", "email"}:
            raise ExecutionDenied("arguments")
        from chatballs.conversations.contact_card import save_card_fields
        _, error = save_card_fields(contact, patch)
        if error:
            raise ExecutionDenied("arguments")
    else:
        from chatballs.conversations.lifecycle_services import (
            close_conversation,
            delete_conversation,
            mark_conversation_as_spam,
        )
        conversation = Conversation.objects.get(pk=link["internal_id"], organization_id=tenant.organization_id)
        if delete:
            delete_conversation(context=tenant, conversation=conversation)
        elif set(patch) == {"status"}:
            if patch["status"] == "closed":
                close_conversation(context=tenant, conversation_id=conversation.pk)
            elif patch["status"] == "spam":
                mark_conversation_as_spam(context=tenant, conversation_id=conversation.pk)
            elif patch["status"] == "waiting":
                from chatballs.conversations.control_services import return_to_queue
                return_to_queue(context=tenant, conversation_id=conversation.pk)
            else:
                # ADR-0001/SPEC-0018 prohibit inventing a reopen transition.
                raise ExecutionDenied("operation_unavailable")
        elif patch:
            raise ExecutionDenied("arguments")
    return record(tenant, link)
