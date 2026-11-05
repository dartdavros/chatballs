"""Public site ingress accepts no scenario, organization or authority selector."""

from django.core.exceptions import ValidationError
from rest_framework.response import Response

from chatballs.i18n import customer_language, t
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.webchat.access import _PublicSession, _resolved_web_session, session_available
from chatballs.webchat.api_inputs import host_origin
from chatballs.webchat.site_event_schema import MAX_ENVELOPE_BYTES
from chatballs.webchat.site_events import receive


class WebchatSiteEventView(_PublicSession):
    def post(self, request):
        if len(request.body) > MAX_ENVELOPE_BYTES:
            return Response({"detail": t("site_events.invalid")}, status=400)
        if not isinstance(request.data, dict):
            return Response({"detail": t("site_events.invalid")}, status=400)
        with _resolved_web_session(request) as (tenant, session):
            if session is None or not session_available(session, request):
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            envelope = {key: value for key, value in request.data.items() if key != "hostOrigin"}
            try:
                claim, created = receive(tenant, session, envelope, origin=host_origin(request))
            except ValidationError:
                return Response({"detail": t("site_events.invalid", language=customer_language(session.organization))}, status=400)
            except ExecutionDenied as error:
                if str(error) == "site_event_suppressed":
                    return Response({"state": "suppressed"})
                return Response({"detail": t("site_events.invalid", language=customer_language(session.organization))}, status=400)
            return Response({"state": "accepted" if created else "duplicate"}, status=202 if created else 200)


class WebchatSiteEventCancelView(_PublicSession):
    def post(self, request):
        from chatballs.webchat.consent import require_current_consent
        from chatballs.webchat.proactive_status import cancel
        with _resolved_web_session(request) as (_, session):
            if session is None or not session_available(session, request):
                return Response({"detail": t("webchat.session_not_found")}, status=401)
            require_current_consent(session)
            cancel(session)
            return Response({"state": "suppressed"})
