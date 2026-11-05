"""Публичное распознавание черновика: здесь нет ingest, Message или очереди."""

from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from chatballs.ai.provider.base import ProviderError
from chatballs.i18n import customer_language, t
from chatballs.speech.concurrency import recognition_lease
from chatballs.speech.contracts import MAX_RECORDING_BYTES
from chatballs.speech.errors import SpeechError
from chatballs.speech.formats import normalize_audio
from chatballs.speech.routing import resolve_model, resolve_transcriber, selected_integration
from chatballs.webchat.access import _PublicSession, _resolved_web_session, session_available
from chatballs.webchat.api_inputs import BEARER_PREFIX
from chatballs.webchat.consent import require_current_consent
from chatballs.webchat.recording_configuration import recording_settings
from chatballs.webchat.speech_inputs import BoundedMemoryUploadHandler


class WebchatDictationView(_PublicSession):
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not request.headers.get("Authorization", "").startswith(BEARER_PREFIX):
            return Response({"detail": t("webchat.session_not_found")}, status=401)
        handler = BoundedMemoryUploadHandler(request._request, MAX_RECORDING_BYTES)
        request._request.upload_handlers = [handler]
        language = None
        upload = None
        try:
            with _resolved_web_session(request) as (_, session):
                if session is None:
                    return Response({"detail": t("webchat.session_not_found")}, status=401)
                language = customer_language(session.connection.organization)
                require_current_consent(session)
                limits = recording_settings(session.connection)
                if limits["microphoneMode"] != "dictation":
                    raise SpeechError("unavailable")
                handler.max_bytes = limits["maxRecordingBytes"]
                if int(request.META.get("CONTENT_LENGTH") or 0) > handler.max_bytes + 65536:
                    raise SpeechError("too_large")
                if not session_available(session, request):
                    raise SpeechError("unavailable")
                provider = resolve_transcriber(session.connection.channel, timeout=40)
                model = resolve_model(session.connection.channel)
                integration_id = selected_integration(session.connection.channel).id
                identifiers = {"session_id": session.id, "widget_id": session.widget_id, "integration_id": integration_id}
            upload = request.FILES.get("audio")
            if upload is None or len(request.FILES) != 1:
                raise SpeechError("format_unsupported")
            with recognition_lease(**identifiers, client_address=request.META.get("REMOTE_ADDR", "")):
                audio = normalize_audio(
                    upload.read(handler.max_bytes + 1), max_bytes=handler.max_bytes,
                    max_seconds=limits["maxDictationSeconds"],
                )
                if hasattr(provider, "recognize_pcm"):
                    text = provider.recognize_pcm(audio.pcm, model=model).strip()
                else:
                    text = provider.transcribe(audio=audio.wav(), filename="dictation.wav", content_type="audio/wav", model=model).strip()
                if not text:
                    raise SpeechError("empty")
                # Не обрезаем: превышение обычной длины остаётся в черновике.
                response = Response({"text": text})
                response["Cache-Control"] = "no-store"
                return response
        except SpeechError as error:
            return Response({"detail": t(f"speech.{error.code}", language=language), "code": error.code}, status=429 if error.code == "busy" else 400)
        except ProviderError:
            return Response({"detail": t("speech.provider_error", language=language), "code": "provider_error"}, status=400)
        finally:
            if upload is not None:
                upload.close()
            elif hasattr(handler, "file"):
                handler.file.close()
