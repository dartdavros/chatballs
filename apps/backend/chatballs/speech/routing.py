"""Выбранный STT → наследуемый STT; неисправный явный выбор не подменяется."""

from chatballs.speech.contracts import capabilities
from chatballs.speech.errors import SpeechError


def selected_integration(channel):
    agent = getattr(channel, "ai_agent", None)
    if agent is None:
        raise SpeechError("unavailable")
    integration = getattr(agent, "transcription_integration", None)
    if integration is None:
        integration = getattr(agent, "provider_integration", None)
    if (
        integration is None or integration.organization_id != channel.organization_id
        or not integration.is_active or integration.status == "ERROR"
        or not integration.secret or not capabilities(integration.provider).stt
    ):
        raise SpeechError("unavailable")
    return integration


def resolve_model(channel) -> str:
    integration = selected_integration(channel)
    contract = capabilities(integration.provider)
    agent = channel.ai_agent
    chosen = (agent.transcription_model or integration.config.get("transcription_model") or contract.default_model).strip()
    if contract.models and chosen not in contract.models:
        raise SpeechError("model_unsupported")
    return chosen


def resolve_transcriber(channel, *, timeout: float | None = None):
    integration = selected_integration(channel)
    if integration.provider == "YANDEX_SPEECHKIT":
        from chatballs.i18n import customer_language
        from chatballs.speech.providers.yandex_stt import YandexSTT

        language = getattr(channel.ai_agent, "transcription_language", "") or customer_language(channel.organization)
        return YandexSTT(
            api_key=integration.secret, folder_id=integration.config.get("folder_id", ""),
            language={"ru": "ru-RU", "en": "en-US"}.get(language, language), timeout=timeout,
        )
    from chatballs.ai.provider.routing import provider_for_integration

    return provider_for_integration(integration, timeout=timeout)
