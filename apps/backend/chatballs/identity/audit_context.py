"""Server-only provenance scoped to one native step, including source audits."""

from contextlib import contextmanager
from contextvars import ContextVar

from chatballs.i18n import t

_native_actor = ContextVar("native_audit_actor", default=None)
KEY = "_nativeActor"


@contextmanager
def native_audit(run, step, actor, *, title_key=""):
    binding = run.definition.get("ai")
    if not binding:
        yield
        return
    agent_name = run.structure.get("agentName", "")
    if not agent_name:
        from chatballs.ai.models import AIAgent
        agent_name = AIAgent.objects.get(pk=binding["agent"], organization_id=run.organization_id).channel.name
    token = _native_actor.set({"organizationId": run.organization_id, "agentId": binding["agent"],
        "agentName": agent_name, "delegateMembershipId": actor.membership_id,
        "runId": str(run.public_id), "stepPath": step.path, "titleKey": title_key})
    try:
        yield
    finally:
        _native_actor.reset(token)


def audit_payload(organization, payload):
    current = _native_actor.get()
    return {**(payload or {}), KEY: dict(current)} if current and organization and (
        current["organizationId"] == organization.pk) else payload or {}


def actor_label(event, fallback):
    metadata = (event.payload or {}).get(KEY, {})
    return t("native.audit_actor", agent=metadata["agentName"], delegate=fallback) if metadata else fallback


def action_label(event, fallback):
    metadata = (event.payload or {}).get(KEY, {})
    return t(metadata["titleKey"]) if event.action == "integrations.native_action_executed" and metadata.get("titleKey") else fallback
