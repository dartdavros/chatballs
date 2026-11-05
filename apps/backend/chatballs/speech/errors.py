from chatballs.ai.provider.base import ProviderError
from chatballs.i18n import t


class SpeechError(ProviderError):
    """Только безопасный код; payload/ответ провайдера не входят в исключение."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(t(f"speech.{code}"))
