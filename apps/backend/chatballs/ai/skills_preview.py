"""HTTP boundaries for shared skill draft validation and preview."""

from rest_framework.response import Response

from chatballs.ai import skills_preview_service as service
from chatballs.ai.skills_views import SkillView


class SkillValidationView(SkillView):
    def post(self, request, skill_id=None):
        raw = self.body(request, ["configuration"])
        return Response(service.validate(request.tenant_context, raw, skill_id))


class SkillPreviewView(SkillView):
    def post(self, request, skill_id=None):
        raw = self.body(request, ["configuration", "templateId", "data"])
        return Response(service.preview(request.tenant_context, raw, skill_id))


class SkillBasisView(SkillView):
    def get(self, request):
        return Response(service.basis(request.tenant_context))
