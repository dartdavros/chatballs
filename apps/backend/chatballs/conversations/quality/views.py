"""HTTP adapters retain quality response status, privacy and validation."""

from rest_framework.response import Response

from chatballs.conversations.view_base import ConversationViewBase

from . import operations
from .queue import MissingCompletionHistory


class QualityViewBase(ConversationViewBase):
    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(exc, MissingCompletionHistory):
            response.data.update(state="unavailable", errorCode="missing_history")
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response


class QualitySettingsView(QualityViewBase):
    required_capability = "settings.manage"

    def get(self, request):
        return Response(operations.settings(request.tenant_context))

    def put(self, request):
        return Response(operations.change_settings(request.tenant_context, request.data))


class QualityLaunchView(QualityViewBase):
    required_capability = "settings.manage"

    def post(self, request, conversation_id):
        return Response(operations.launch(request.tenant_context, conversation_id, request.data), status=202)


class QualityConversationView(QualityViewBase):
    def get(self, request, conversation_id):
        return Response(operations.conversation_jobs(request.tenant_context, conversation_id))


class QualityJobView(QualityViewBase):
    def get(self, request, job_id):
        return Response(operations.job(request.tenant_context, job_id))


class QualityReportView(QualityViewBase):
    def get(self, request):
        return Response(operations.report(request.tenant_context, request.query_params))


class QualityCorrectionView(QualityViewBase):
    def post(self, request, job_id):
        return Response(operations.correct(request.tenant_context, job_id, request.data))


class QualityEvidenceView(QualityViewBase):
    def get(self, request, job_id, message_id):
        return Response(operations.evidence(request.tenant_context, job_id, message_id))
