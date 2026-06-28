from hub_platform.conversations.transports import max as _max
from hub_platform.conversations.transports import telegram as _telegram
from hub_platform.integrations.models import IntegrationProvider

_POLL = {
    IntegrationProvider.MAX: _max.poll_updates,
    IntegrationProvider.TELEGRAM: _telegram.poll_updates,
}
_SEND = {
    IntegrationProvider.MAX: _max.send_text,
    IntegrationProvider.TELEGRAM: _telegram.send_text,
}

# Провайдеры-мессенджеры, у которых есть транспорт приёма/отправки.
SUPPORTED_PROVIDERS = tuple(_POLL.keys())


def poll(integration):
    return _POLL[integration.provider](integration)


def send_reply(integration, *, chat_id: str, user_id: str, text: str) -> bool:
    return _SEND[integration.provider](integration, chat_id=chat_id, user_id=user_id, text=text)
