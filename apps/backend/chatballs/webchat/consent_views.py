"""Актуальное согласие существующей сессии без создания нового контакта."""

from rest_framework.response import Response

from chatballs.i18n import t
from chatballs.webchat.access import _PublicSession, _resolved_web_session, session_available
from chatballs.webchat.consent import has_current_consent, record_acceptance
from chatballs.webchat.site_fields import save_site_fields


class WebchatConsentView(_PublicSession):
    def get(self, request):
        with _resolved_web_session(request) as (_, session):
            if session is None or not session_available(session, request):
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            response = Response({"accepted": has_current_consent(session)})
            response["Cache-Control"] = "no-store"
            return response

    def post(self, request):
        with _resolved_web_session(request) as (_, session):
            if session is None or not session_available(session, request):
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            fields = request.data.get("preChatFields")
            record_acceptance(session, version=request.data.get("consentVersion"), fields=fields)
            if fields is not None:
                save_site_fields(session, fields)
            return Response({"accepted": True})
