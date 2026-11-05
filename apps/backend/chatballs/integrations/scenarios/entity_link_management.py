"""Visible linked records and explicit replacement based on a completed search."""


from chatballs.conversations.access import require_conversation_action
from chatballs.conversations.models import Conversation
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.execution.permissions import ExecutionDenied, view_run
from chatballs.integrations.scenario_state.entity_links import EntityLink
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenarios.entity_links import link, snapshot
from chatballs.integrations.service_connections.binding import load_credentials, resolve
from chatballs.tenancy.database import tenant_atomic


def conversation_for(tenant, identity, capability):
    identity = str(identity)
    if not identity.isdecimal() or len(identity) > 15:
        raise Conversation.DoesNotExist
    row = Conversation.objects.get(pk=int(identity), organization_id=tenant.organization_id)
    require_conversation_action(tenant, row, capability)
    return row


def linked(tenant, identity, pk, capability):
    conversation = conversation_for(tenant, identity, capability)
    identities = [row["id"] for row in snapshot(conversation)]
    row = EntityLink.objects.select_related("integration").get(pk=pk, pk__in=identities)
    _, adapter, _ = resolve(row.integration)
    entity = next((e for e in adapter.entities if e.key == row.external_kind), None)
    if entity is None:
        raise ExecutionDenied("operation_unavailable")
    return conversation, row, entity


def listing(tenant, identity):
    with tenant_atomic(tenant):
        conversation = conversation_for(tenant, identity, "conversations.view")
        items = []
        for saved in snapshot(conversation):
            row = EntityLink.objects.select_related("integration").get(pk=saved["id"])
            settings, adapter, _ = resolve(row.integration)
            entity = next((e for e in adapter.entities if e.key == row.external_kind), None)
            url = ""
            if entity and entity.references and entity.references.record_url:
                from urllib.parse import urlsplit
                candidate = entity.references.record_url(load_credentials(settings), row.external_id)
                parsed = urlsplit(candidate)
                if parsed.scheme == "https" and parsed.hostname and not (parsed.username or parsed.password or parsed.query or parsed.fragment):
                    url = candidate
            items.append({"id": row.pk, "name": f"{t(entity.title_key) if entity else t('scenarios.external_id')} · {row.external_id}",
                "service": row.integration.name, "revision": row.revision, "searchable": bool(entity and entity.references), "url": url})
        return {"items": items}


def candidates(tenant, row, entity, conversation, public_id):
    run = ScenarioRun.objects.get(public_id=public_id, organization_id=tenant.organization_id, conversation=conversation)
    view_run(tenant, run)
    if (not entity.references or run.scenario_key != f"operation:{row.integration_id}:{entity.references.operation}"):
        raise ExecutionDenied("permission")
    if run.state != "completed" or run.data_cleared_at:
        return run.state, []
    items = entity.references.candidates(run.steps.get().definition["result"])
    if len(items) > 100 or any(not isinstance(i.id, str) or not 1 <= len(i.id) <= 512 or not isinstance(i.label, str) or len(i.label) > 1000 for i in items):
        raise ExecutionDenied("arguments")
    return run.state, [{"id": item.id, "label": item.label} for item in items]


def search_results(tenant, identity, pk, public_id):
    with tenant_atomic(tenant):
        conversation, row, entity = linked(tenant, identity, pk, "conversations.operate")
        state, items = candidates(tenant, row, entity, conversation, public_id)
        return {"state": state, "items": items}


def change(tenant, identity, pk, data, *, request=None):
    with tenant_atomic(tenant):
        conversation, row, entity = linked(tenant, identity, pk, "conversations.operate")
        from chatballs.integrations.models import Integration
        Integration.objects.select_for_update().get(pk=row.integration_id)
        row = EntityLink.objects.select_for_update().get(pk=row.pk)
        if type(data.get("revision")) is not int or row.revision != data["revision"]:
            raise ExecutionDenied("state_changed")
        action = data.get("action")
        if action == "unlink":
            row.active, row.revision = False, row.revision + 1
            row.save(update_fields=["active", "revision", "updated_at"])
        elif action == "replace":
            state, items = candidates(tenant, row, entity, conversation, data.get("searchRunId"))
            identity = data.get("externalId")
            if state != "completed" or not any(item["id"] == identity for item in items):
                raise ExecutionDenied("arguments")
            link(tenant, conversation, row.integration_id, row.external_kind, identity, revision=row.revision, replace=True)
        else:
            raise ExecutionDenied("arguments")
        record_audit_event(action=f"integrations.entity_link_{action}", actor=tenant.actor_user, organization=tenant.organization,
            object_type="EntityLink", object_id=str(row.pk), payload={}, request=request)
        from django.db import transaction

        from chatballs.conversations.realtime import conversation_group, inbox_group
        from chatballs.realtime import publish
        groups = (conversation_group(conversation.pk), inbox_group(conversation.organization_id))
        transaction.on_commit(lambda: [publish(group, {"type": "service_runs.changed"}) for group in groups])
        return {"updated": True}
