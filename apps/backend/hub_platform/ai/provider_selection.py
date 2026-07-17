from django.conf import settings
from django.core.exceptions import ValidationError

from hub_platform.ai.models import CredentialMode
from hub_platform.channels.models import Channel
from hub_platform.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
)
from hub_platform.tenancy.context import TenantContext


def configure_agent_provider(
    *, context: TenantContext, channel: Channel, mode: str, integration_id: int | None
) -> tuple[str, str]:
    if mode not in CredentialMode.values:
        raise ValidationError({"credentialMode": "Unknown credential mode"})
    if mode == CredentialMode.CUSTOAI:
        return mode, settings.HUB_CUSTOAI_MODEL
    if integration_id is None:
        raise ValidationError({"providerIntegrationId": "BYOK integration is required"})
    try:
        integration = Integration.objects.get(
            id=integration_id,
            organization_id=context.organization_id,
            kind=IntegrationKind.LLM_PROVIDER,
            provider__in=[IntegrationProvider.OPENROUTER, IntegrationProvider.CUSTOM],
        )
    except (Integration.DoesNotExist, TypeError, ValueError) as error:
        raise ValidationError(
            {"providerIntegrationId": "Unknown OpenRouter or Custom integration"}
        ) from error
    model = str(integration.config.get("default_model", "")).strip()
    if not model:
        raise ValidationError(
            {"providerIntegrationId": "Integration default model is required"}
        )
    if channel.provider_integration_id != integration.id:
        channel.provider_integration = integration
        channel.save(update_fields=["provider_integration", "updated_at"])
    return mode, model
