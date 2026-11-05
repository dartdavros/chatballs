"""Thin administrative HTTP boundary for the organization skill library."""

from django.core.exceptions import RequestDataTooBig
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler

from chatballs.ai.skill_templates.errors import TemplateError
from chatballs.ai.skills_json import SkillJSONParser
from chatballs.ai.skills_queries import listing, load, require_manager, skill_payload
from chatballs.ai.skills_service import (
    delete_configuration,
    save_configuration,
    set_assignment,
)
from chatballs.ai.skills_validation import REQUEST_MAX_BYTES, SkillError


class SkillView(APIView):
    parser_classes = [SkillJSONParser]

    def perform_authentication(self, request):
        # SessionAuthentication's CSRF check may parse request.data. Cache the
        # bounded body first, so the later envelope check can read it safely.
        try:
            if int(request.META.get("CONTENT_LENGTH") or 0) > REQUEST_MAX_BYTES:
                raise SkillError("request_too_large", status=413)
            if len(request.body) > REQUEST_MAX_BYTES:
                raise SkillError("request_too_large", status=413)
        except RequestDataTooBig:
            raise SkillError("request_too_large", status=413) from None
        except ValueError:
            raise SkillError("invalid_request") from None
        super().perform_authentication(request)

    def get_exception_handler(self):
        # This API needs field paths and machine-readable conflicts. The legacy
        # SPA handler flattens them; keep its behavior unchanged for other APIs.
        return exception_handler

    def check_permissions(self, request):
        super().check_permissions(request)
        context = getattr(request, "tenant_context", None)
        if context is None:
            raise SkillError("forbidden", status=403)
        require_manager(context)

    def handle_exception(self, exc):
        if isinstance(exc, APIException) and not isinstance(exc, SkillError | TemplateError):
            code = "forbidden" if exc.status_code in (401, 403) else "invalid_request"
            exc = SkillError(code, status=exc.status_code)
        return super().handle_exception(exc)

    def body(self, request, fields):
        try:
            size = len(request.body)
        except RequestDataTooBig:
            raise SkillError("request_too_large", status=413) from None
        if size > REQUEST_MAX_BYTES:
            raise SkillError("request_too_large", status=413)
        try:
            raw = request.data
        except (RecursionError, ValueError):
            raise SkillError("invalid_request") from None
        if not isinstance(raw, dict) or set(raw) != set(fields):
            raise SkillError("invalid_request")
        return raw


class SkillListView(SkillView):
    def get(self, request):
        return Response(listing(request.tenant_context, request.query_params))

    def post(self, request):
        raw = self.body(request, ["requestId", "configuration"])
        skill, created = save_configuration(
            context=request.tenant_context, raw=raw["configuration"], request_id=raw["requestId"],
        )
        return Response({"skill": skill_payload(skill, full=True)}, status=201 if created else 200)


class SkillDetailView(SkillView):
    def get(self, request, skill_id):
        return Response({"skill": skill_payload(load(request.tenant_context, skill_id), full=True)})

    def put(self, request, skill_id):
        raw = self.body(request, ["requestId", "expectedRevision", "configuration"])
        skill, _ = save_configuration(
            context=request.tenant_context, raw=raw["configuration"], request_id=raw["requestId"],
            public_id=skill_id, revision=raw["expectedRevision"],
        )
        return Response({"skill": skill_payload(skill, full=True)})

    def delete(self, request, skill_id):
        raw = self.body(request, ["expectedRevision"])
        delete_configuration(context=request.tenant_context, public_id=skill_id, revision=raw["expectedRevision"])
        return Response(status=204)


class SkillDeletionView(SkillView):
    def get(self, request, skill_id):
        skill = load(request.tenant_context, skill_id)
        result = skill_payload(skill)
        return Response({"skill": result, "confirmationRequired": True})


class SkillAssignmentView(SkillView):
    def _set(self, request, skill_id, agent_id, enabled):
        raw = self.body(request, ["expectedRevision"])
        skill = set_assignment(
            context=request.tenant_context, public_id=skill_id, agent_id=agent_id,
            enabled=enabled, revision=raw["expectedRevision"],
        )
        return Response({"skill": skill_payload(skill)})

    def put(self, request, skill_id, agent_id):
        return self._set(request, skill_id, agent_id, True)

    def delete(self, request, skill_id, agent_id):
        return self._set(request, skill_id, agent_id, False)
