"""Проверка WEB-голосового до сохранения; исходная запись остаётся сообщением."""

from rest_framework.response import Response

from chatballs.i18n import customer_language, t
from chatballs.speech.errors import SpeechError
from chatballs.speech.formats import recording_duration
from chatballs.webchat import services
from chatballs.webchat.access import _resolved_web_session, session_available
from chatballs.webchat.consent import require_current_consent
from chatballs.webchat.recording_configuration import recording_settings


def _limits(session, request):
    require_current_consent(session)
    limits = recording_settings(session.connection)
    if limits["microphoneMode"] != "voice_message" or not session_available(session, request):
        raise SpeechError("unavailable")
    return limits


def post_web_voice(request, upload):
    language = None
    try:
        with _resolved_web_session(request) as (_, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            language = customer_language(session.connection.organization)
            limits = _limits(session, request)
        content = upload.read(limits["maxRecordingBytes"] + 1)
        content_type, seconds = recording_duration(content, max_bytes=limits["maxRecordingBytes"])
        with _resolved_web_session(request) as (_, session):
            if session is None:
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            current = _limits(session, request)
            if len(content) > current["maxRecordingBytes"]:
                raise SpeechError("too_large")
            services.post_voice(session, content=content, content_type=content_type, duration=max(1, round(seconds)))
        return Response({"ok": True}, status=201)
    except SpeechError as error:
        return Response({"detail": t(f"speech.{error.code}", language=language)}, status=400)
