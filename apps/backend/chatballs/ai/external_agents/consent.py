"""External export changes invalidate the server's saved WEB consent and form revision."""

from django.core.exceptions import ObjectDoesNotExist

from chatballs.identity.demo_seed.north_wind.executor_scope import execution_enabled


def external_disclosure(widget):
    try:
        agent = widget.integration.channel.ai_agent
        binding = agent.external_binding
    except (ObjectDoesNotExist, AttributeError):
        return None
    organization = widget.organization
    if agent.execution_mode != "external" or not execution_enabled(organization, binding.connection, agent_id=agent.pk):
        return None
    from chatballs.ai.external_agents.custom_field_revisions import fingerprint

    return {"feature": organization.external_execution_version,
            "disclosure": 1, "serviceName": binding.connection.integration.name,
            "execution": agent.execution_version, "binding": binding.pk,
            "policy": binding.policy_version, "configuration": binding.connection.revision,
            "exportPolicy": fingerprint(binding)}


def disclosure_html(widget, *, language):
    from html import escape

    from chatballs.i18n import t

    disclosure = external_disclosure(widget)
    if not disclosure:
        return ""
    return "<p>" + t("external.consent_messages", language=language,
                      service=escape(disclosure["serviceName"])) + "</p><p>" + t(
                          "external.consent_voice", language=language) + "</p>"
