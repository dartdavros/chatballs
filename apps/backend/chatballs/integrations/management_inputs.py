"""Product integration input normalization, shared by HTTP and native commands."""

from chatballs.integrations.models import Integration
from chatballs.integrations.operator_routes import UNSET_GROUP
from chatballs.integrations.serializers import restore_proxy_password
from chatballs.integrations.services import IntegrationInput


def integration_input(body: dict[str, object], *, current: Integration | None = None) -> IntegrationInput:
    config = body.get("config", current.config if current else {})
    config = _keep_proxy_password(config, current)
    raw_channel = body.get("channelId", current.channel_id if current else None)
    channel_id = int(raw_channel) if isinstance(raw_channel, int) or (isinstance(raw_channel, str) and raw_channel.isdigit()) else None
    return IntegrationInput(
        provider=str(body.get("provider", current.provider if current else "")),
        name=str(body.get("name", current.name if current else "")),
        secret=body.get("secret") if "secret" in body else None,
        config=config if isinstance(config, dict) else {},
        channel_id=channel_id,
        is_active=(
            body["isActive"]
            if isinstance(body.get("isActive"), bool)
            else (current.is_active if current else None)
        ),
        external=body.get("externalServer"),
        group_id=body.get("groupId", UNSET_GROUP),
    )


def _keep_proxy_password(config: object, current: Integration | None) -> object:
    """Маска пароля прокси из ответа не должна затирать настоящий пароль."""
    if not isinstance(config, dict) or current is None:
        return config
    submitted = str(config.get("proxyUrl", config.get("proxy_url", "")) or "")
    if not submitted:
        return config
    restored = restore_proxy_password(submitted, str(current.config.get("proxy_url", "")))
    if restored == submitted:
        return config
    config = dict(config)
    config.pop("proxy_url", None)
    config["proxyUrl"] = restored
    return config


