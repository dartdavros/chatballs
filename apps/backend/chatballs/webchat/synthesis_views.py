"""Manual synthesis: authorize in a short tenant transaction, then bounded I/O."""

from django.http import HttpResponse
from rest_framework.response import Response

from chatballs.i18n import customer_language, t
from chatballs.speech.concurrency import recognition_lease
from chatballs.speech.errors import SpeechError
from chatballs.speech.providers.yandex_tts import MAX_TEXT
from chatballs.speech.synthesis import resolve_synthesis
from chatballs.speech.tts_contract import validate_language
from chatballs.webchat.access import _PublicSession, _resolved_web_session, session_available
from chatballs.webchat.api_inputs import BEARER_PREFIX
from chatballs.webchat.consent import require_current_consent
from chatballs.webchat.speech_selectors import synthesis_message


class WebchatSynthesisView(_PublicSession):
    def post(self, request, message_id):
        language = None
        if not request.headers.get("Authorization", "").startswith(BEARER_PREFIX):
            return Response(status=401)
        try:
            if not isinstance(request.data, dict) or set(request.data) - {"hostOrigin", "revision"}:
                raise SpeechError("tts_unavailable")
            with _resolved_web_session(request) as (_, session):
                if session is None:
                    return Response(status=401)
                language = customer_language(session.connection.organization)
                if not session_available(session, request):
                    raise SpeechError("tts_unavailable")
                require_current_consent(session)
                provider, revision, integration_id = resolve_synthesis(session.connection)
                if request.data.get("revision") != revision:
                    raise SpeechError("tts_changed")
                message = synthesis_message(session, message_id)
                text = message.text
                if len(text) > MAX_TEXT:
                    raise SpeechError("tts_text_limit")
                identifiers = {"session_id": session.id, "widget_id": session.widget_id, "integration_id": integration_id}
            validate_language(text, provider.voice)
            with recognition_lease(**identifiers, client_address=request.META.get("REMOTE_ADDR", ""), seconds=190):
                audio = provider.synthesize(text)
            # Settings/consent can change while the external request is running.
            with _resolved_web_session(request) as (_, session):
                if session is None or not session_available(session, request):
                    raise SpeechError("tts_unavailable")
                require_current_consent(session)
                if resolve_synthesis(session.connection)[1] != revision or synthesis_message(session, message_id).text != text:
                    raise SpeechError("tts_changed")
            response = HttpResponse(audio, content_type="audio/wav")
            response["Cache-Control"] = "no-store, private"
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except SpeechError as error:
            code = {"provider_error": "tts_provider_error", "timeout": "tts_timeout", "access_denied": "tts_provider_error"}.get(error.code, error.code)
            return Response({"code": code, "detail": t(f"speech.{code}", language=language)}, status=429 if code == "busy" else 400)
