"""External admission, independent of builtin provider/model readiness."""

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from chatballs.ai.external_agents.adapter import PROFILE


def require_builtin(agent, *, assistance=False):
    if agent.execution_mode != "builtin" and not (
        assistance and agent.assistance_enabled and agent.provider_integration_id is not None
    ):
        from chatballs.i18n import t

        raise ValidationError(t("external.not_builtin"))


def ready(agent, organization):
    try:
        binding = agent.external_binding
        connection = binding.connection
        integration = connection.integration
        service = integration.service_settings
    except ObjectDoesNotExist:
        return False
    from chatballs.ai.external_agents.config_policy import policy_values
    from chatballs.tenancy.context import TenantContext

    try:
        # An edited/deleted optional template is a formatted-item conflict,
        # not revocation of the independently configured executor or text replies.
        policy_values(TenantContext.for_resource(organization), {}, binding, check_template_selection=False)
    except ValidationError:
        return False
    from chatballs.ai.external_agents.grant_definitions import stale_grants

    if stale_grants(binding)["customFields"]:
        return False
    return bool(
        organization.external_execution_enabled and agent.execution_mode == "external"
        and agent.organization_id == organization.pk
        and binding.organization_id == organization.pk and binding.enabled
        and binding.external_agent_id and binding.policy_accepted
        and connection.organization_id == organization.pk and connection.enabled
        and connection.inbound_key_hash and connection.checked_at and connection.capabilities
        and integration.organization_id == organization.pk and integration.is_active
        and integration.kind == "SERVICE" and integration.provider == "ADAPTER"
        and service.adapter_key == PROFILE and service.adapter_version == 1
        and service.auth_method == "bearer" and service.credentials
    )


def consent_current(conversation):
    if conversation.connection is None or conversation.connection.provider != "WEB":
        return True
    from chatballs.webchat.consent import has_current_consent
    from chatballs.webchat.models import WebSession

    sessions = WebSession.objects.filter(
        organization_id=conversation.organization_id, connection_id=conversation.connection_id,
        identity__contact_id=conversation.contact_id,
    ).select_related("widget__integration__channel__ai_agent")
    return any(session.widget.consent_config.get("consent_text") and has_current_consent(session)
               for session in sessions)
