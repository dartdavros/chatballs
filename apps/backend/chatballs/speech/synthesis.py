"""TTS configuration snapshot, safe public revision and explicit routing."""

import hashlib
import json

from chatballs.speech.errors import SpeechError
from chatballs.speech.providers.yandex_tts import YandexTTS
from chatballs.speech.tts_contract import validate_selection


def resolve_synthesis(connection):
    agent = getattr(connection.channel, "ai_agent", None)
    integration = getattr(agent, "synthesis_integration", None)
    if (not connection.config.get("answerPlaybackEnabled", False) or agent is None
            or agent.organization_id != connection.organization_id or not agent.is_active
            or integration is None or integration.organization_id != connection.organization_id
            or integration.provider != "YANDEX_SPEECHKIT" or not integration.is_active
            or not integration.secret or not agent.synthesis_voice):
        raise SpeechError("tts_unavailable")
    from chatballs.identity.operation_modes import autonomous_allowed

    if not autonomous_allowed(connection.channel, organization=connection.organization, connection=connection):
        raise SpeechError("tts_unavailable")
    validate_selection(agent.synthesis_model, agent.synthesis_voice)
    revision = hashlib.sha256(json.dumps([
        connection.id, connection.config.get("answerPlaybackEnabled"),
        agent.id, agent.updated_at.isoformat(), integration.id, integration.runtime_revision,
        agent.synthesis_model, agent.synthesis_voice,
    ]).encode()).hexdigest()
    return YandexTTS(api_key=integration.secret, folder_id=integration.config.get("folder_id", ""),
                     model=agent.synthesis_model, voice=agent.synthesis_voice), revision, integration.id


def public_synthesis(connection):
    try:
        _, revision, _ = resolve_synthesis(connection)
        return {"playbackAvailable": True, "ttsRevision": revision}
    except SpeechError:
        return {"playbackAvailable": False, "ttsRevision": ""}
