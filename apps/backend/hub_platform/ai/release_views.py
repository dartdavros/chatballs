from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.ai import limits, pricing
from hub_platform.ai import releases as release_service
from hub_platform.ai.models import ChannelAIRelease, ReleaseStatus
from hub_platform.ai.provider.base import ProviderError
from hub_platform.ai.runtime import run_test_chat
from hub_platform.ai.selectors import release_for_organization, releases_for_organization
from hub_platform.ai.serializers import release_payload
from hub_platform.api.permissions import IsOwner
from hub_platform.channels.models import Channel
from hub_platform.identity.audit import record_audit_event


class _ReleaseBase(APIView):
    permission_classes = [IsOwner]

    def _org(self, request: Request):
        return request.user.employee_profile.organization

    def _release(self, request: Request, release_id: int) -> ChannelAIRelease:
        return release_for_organization(organization_id=self._org(request).id, release_id=release_id)

    def _audit(self, request: Request, action: str, release: ChannelAIRelease) -> None:
        record_audit_event(
            action=f"ai.release_{action}",
            actor=request.user,
            organization=self._org(request),
            object_type="ChannelAIRelease",
            object_id=str(release.id),
            request=request,
        )


class ReleaseListCreateView(_ReleaseBase):
    def get(self, request: Request) -> Response:
        releases = releases_for_organization(self._org(request).id, request.query_params.get("channel"))
        return Response({"items": [release_payload(release) for release in releases]})

    def post(self, request: Request) -> Response:
        try:
            channel = Channel.objects.select_related("ai_agent").get(
                organization=self._org(request), code=str(request.data.get("channel", ""))
            )
        except Channel.DoesNotExist:
            return Response({"detail": "Channel not found"}, status=400)
        release = release_service.create_draft_release(
            channel=channel, author=request.user, notes=str(request.data.get("notes", ""))
        )
        release = self._release(request, release.id)
        self._audit(request, "drafted", release)
        return Response({"release": release_payload(release)}, status=201)


class ReleaseDetailView(_ReleaseBase):
    def get(self, request: Request, release_id: int) -> Response:
        try:
            release = self._release(request, release_id)
        except ChannelAIRelease.DoesNotExist:
            return Response({"detail": "Release not found"}, status=404)
        return Response({"release": release_payload(release)})


class ReleasePublishView(_ReleaseBase):
    def post(self, request: Request, release_id: int) -> Response:
        try:
            release = self._release(request, release_id)
        except ChannelAIRelease.DoesNotExist:
            return Response({"detail": "Release not found"}, status=404)
        if release.status == ReleaseStatus.PUBLISHED:
            return Response({"detail": "Release is already published"}, status=400)
        release_service.publish_release(release=release)
        release = self._release(request, release_id)
        self._audit(request, "published", release)
        return Response({"release": release_payload(release)})


class ReleaseRollbackView(_ReleaseBase):
    def post(self, request: Request, release_id: int) -> Response:
        try:
            source = self._release(request, release_id)
        except ChannelAIRelease.DoesNotExist:
            return Response({"detail": "Release not found"}, status=404)
        draft = release_service.rollback_to_release(channel=source.channel, source=source, author=request.user)
        draft = self._release(request, draft.id)
        self._audit(request, "rolled_back", draft)
        return Response({"release": release_payload(draft)}, status=201)


class ReleaseTestChatView(_ReleaseBase):
    def post(self, request: Request, release_id: int) -> Response:
        try:
            release = self._release(request, release_id)
        except ChannelAIRelease.DoesNotExist:
            return Response({"detail": "Release not found"}, status=404)
        message = str(request.data.get("message", "")).strip()
        if not message:
            return Response({"detail": "Message is required"}, status=400)
        history = request.data.get("history") or []
        try:
            outcome = run_test_chat(release=release, message=message, history=history)
        except limits.LimitExceeded as error:
            return Response({"detail": str(error)}, status=429)
        except ProviderError as error:
            return Response({"detail": str(error)}, status=502)
        result = outcome.result
        return Response(
            {
                "reply": result.text,
                "model": result.model,
                "promptTokens": result.prompt_tokens,
                "completionTokens": result.completion_tokens,
                "totalTokens": result.total_tokens,
                "costMicros": pricing.cost_micros(result.model, result.prompt_tokens, result.completion_tokens),
                "handoffSuggested": outcome.handoff_suggested,
                "usedKnowledge": [
                    {
                        "document": fragment.version.document.code,
                        "version": fragment.version.version,
                        "chunkIndex": fragment.chunk_index,
                        "snippet": fragment.content[:200],
                    }
                    for fragment in outcome.fragments
                ],
                "release": {"id": release.id, "version": release.version, "status": release.status},
            }
        )
