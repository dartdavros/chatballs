from chatballs.products.models import Product


def _channel_payload(channel: object) -> dict[str, object]:
    # Единый источник каналов продукта: connections + agent, чтобы не
    # дублировать выборку отдельным запросом /api/v1/channels/.
    agent = getattr(channel, "ai_agent", None)
    return {
        "id": channel.id,
        "code": channel.code,
        "name": channel.name,
        "isActive": channel.is_active,
        "agentId": agent.id if agent else None,
        "connections": [
            {
                "id": connection.id,
                "provider": connection.provider,
                "name": connection.name,
                "status": connection.status,
            }
            for connection in sorted(channel.connections.all(), key=lambda item: item.id)
        ],
    }


def product_payload(product: Product) -> dict[str, object]:
    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "status": product.status,
        "siteUrl": product.site_url,
        "channels": [_channel_payload(channel) for channel in product.channels.all()],
        "createdAt": product.created_at.isoformat(),
        "updatedAt": product.updated_at.isoformat(),
    }
