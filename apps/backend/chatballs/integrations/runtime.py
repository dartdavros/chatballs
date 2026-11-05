from chatballs.integrations.models import Integration, IntegrationKind


def advance_revision_after_configuration_change(
    integration: Integration,
    *,
    previous_config: dict,
    previous_secret: str,
) -> None:
    if integration.kind in {IntegrationKind.LLM_PROVIDER, IntegrationKind.SPEECH_PROVIDER} and (
        integration.config != previous_config or integration.secret != previous_secret
    ):
        integration.runtime_revision += 1


def advance_revision_after_successful_check(integration: Integration) -> bool:
    if integration.kind not in {IntegrationKind.LLM_PROVIDER, IntegrationKind.SPEECH_PROVIDER}:
        return False
    integration.runtime_revision += 1
    return True
