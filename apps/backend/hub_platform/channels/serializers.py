from hub_platform.channels.models import Channel


def channel_payload(channel: Channel) -> dict[str, object]:
    return {
        "id": channel.id,
        "code": channel.code,
        "name": channel.name,
        "product": {"code": channel.product.code, "name": channel.product.name} if channel.product_id else None,
        "department": channel.department.code if channel.department_id else None,
        "providerIntegrationId": channel.provider_integration_id,
        "agentId": channel.ai_agent.id if hasattr(channel, "ai_agent") else None,
        "isActive": channel.is_active,
        # Политика канала (SPEC-HUB-0010 §4.2): определяет режим sales/support.
        "requiresAuthenticatedProductIdentity": (
            channel.requires_authenticated_product_identity
        ),
        "allowAnonymousSessions": channel.allow_anonymous_sessions,
        "allowSelfReportedContact": channel.allow_self_reported_contact,
        "allowSalesAttribution": channel.allow_sales_attribution,
        "allowCheckoutActions": channel.allow_checkout_actions,
        "createdAt": channel.created_at.isoformat(),
        "updatedAt": channel.updated_at.isoformat(),
    }
