"""Minimal customer status; technical failure detail stays in the scenario journal."""

from chatballs.identity.operation_modes import lock_organization
from chatballs.webchat.proactive_models import SiteEventLaunch


def status(session):
    row = SiteEventLaunch.objects.filter(session=session, organization_id=session.organization_id).order_by("-pk").first()
    if row is None:
        return None
    if row.state in {"pending", "running"}:
        from chatballs.webchat.proactive_guards import expired
        if expired(row):
            return "suppressed"
        if row.receipt_id and row.receipt.deliveries.filter(state="skipped").exists():
            return "suppressed"
        if row.receipt_id and row.receipt.deliveries.filter(run__state__in=("completed", "cancelled")).exists():
            return "suppressed"
        if row.receipt_id and row.receipt.deliveries.filter(state="failed").exists():
            return "failed"
        if row.receipt_id and row.receipt.deliveries.filter(run__state__in=("failed", "unknown")).exists():
            return "failed"
    return row.state


def cancel(session):
    from chatballs.ai.execution_version import configuration_version
    from chatballs.integrations.models import Integration
    from chatballs.webchat.site_events import digest_rule

    organization = lock_organization(session.organization_id)
    integration = Integration.objects.select_for_update(of=("self",)).select_related("channel__ai_agent").get(
        pk=session.connection_id, organization_id=session.organization_id)
    rule = integration.config.get("siteEvent")
    if rule:
        agent = getattr(integration.channel, "ai_agent", None)
        # Also fence an ingress request that has not acquired the organization
        # lock yet. No payload, receipt, Run or conversation is manufactured.
        SiteEventLaunch.objects.get_or_create(session=session, rule_id=rule["id"], defaults={
            "organization": organization, "rule_digest": digest_rule(rule), "origin": "",
            "mode_version": organization.operation_mode_version, "agent_id_snapshot": getattr(agent, "pk", 0),
            "agent_version": configuration_version(agent), "state": "suppressed"})
    SiteEventLaunch.objects.filter(session=session, organization_id=session.organization_id,
        state__in=("pending", "running")).update(state="suppressed")
