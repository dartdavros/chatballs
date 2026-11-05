from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.speech.contracts import capabilities


def validate_agent_speech(agent, *, language: object) -> None:
    if not isinstance(language, str) or language not in {"", "ru-RU", "en-US"}:
        raise ValidationError({"transcriptionLanguage": t("speech.language_unsupported")})
    integration = agent.transcription_integration or agent.provider_integration
    if integration is None:
        return
    contract = capabilities(integration.provider)
    if contract.models and agent.transcription_model and agent.transcription_model not in contract.models:
        raise ValidationError({"transcriptionModel": t("speech.model_unsupported")})
