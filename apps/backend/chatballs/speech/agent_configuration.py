from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.speech.contracts import capabilities


def configure_agent_synthesis(context, agent, *, integration_id, model, voice):
    from chatballs.integrations.models import Integration
    from chatballs.speech.errors import SpeechError
    from chatballs.speech.tts_contract import validate_selection

    if integration_id is not None and type(integration_id) is not int:
        raise ValidationError({"synthesisIntegrationId": t("api.integer_id_required")})
    if not isinstance(model, str) or not isinstance(voice, str):
        raise ValidationError({"synthesisVoice": t("speech.voice_unavailable")})
    integration = None
    if integration_id is not None:
        integration = Integration.objects.filter(id=integration_id, organization_id=context.organization_id,
                                                 kind="SPEECH_PROVIDER", provider="YANDEX_SPEECHKIT").first()
        if integration is None:
            raise ValidationError({"synthesisIntegrationId": t("ai.unknown_provider_integration")})
    try:
        validate_selection(model, voice)
    except SpeechError as error:
        raise ValidationError({"synthesisVoice": str(error)}) from None
    agent.synthesis_integration = integration
    agent.synthesis_model = model
    agent.synthesis_voice = voice


def validate_agent_speech(agent, *, language: object) -> None:
    if not isinstance(language, str) or language not in {"", "ru-RU", "en-US"}:
        raise ValidationError({"transcriptionLanguage": t("speech.language_unsupported")})
    integration = agent.transcription_integration or agent.provider_integration
    if integration is None:
        return
    contract = capabilities(integration.provider)
    if contract.models and agent.transcription_model and agent.transcription_model not in contract.models:
        raise ValidationError({"transcriptionModel": t("speech.model_unsupported")})
