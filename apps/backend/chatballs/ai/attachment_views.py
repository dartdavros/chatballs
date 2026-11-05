from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from chatballs.ai.attachment_reads import open_attachment
from chatballs.ai.models import KnowledgeAttachment


class AttachmentDownloadView(APIView):
    # Public access remains bound to the unguessable UUID and scoped ingress.
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, public_id):
        try:
            stream, name, _content_type = open_attachment(public_id)
        except KnowledgeAttachment.DoesNotExist:
            raise Http404 from None
        return FileResponse(stream, as_attachment=True, filename=name)
