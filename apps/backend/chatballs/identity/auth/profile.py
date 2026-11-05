"""Personal profile HTTP adapters; credential ceremonies remain separate."""
from django.http import FileResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from chatballs.identity import profile_commands, profile_files, profile_language, profile_sessions
from chatballs.identity.auth.profile_credentials import (  # noqa: F401
    ChangeTemporaryPasswordView,
    ProfilePasswordView,
    ProfileTotpDisableView,
    ProfileTotpStartView,
)
from chatballs.identity.command_http import command_response


class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return command_response(profile_commands.update(request.user, request.data, request=request))


class ProfileAppearanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return command_response(profile_commands.appearance(request.user, request.data, request=request))


class ProfileLanguageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return command_response(profile_language.update(request.user, request.data, request=request))


class ProfileAvatarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        stream, content_type = profile_files.read(request.user)
        return FileResponse(stream, content_type=content_type, filename="avatar")

    def post(self, request):
        return command_response(profile_files.upload(request.user, request.FILES.get("file"), request=request))

    def delete(self, request):
        return command_response(profile_files.delete(request.user, request=request))


class ProfileSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return command_response(profile_sessions.read(request.user, request.session.session_key))


class ProfileRevokeOtherSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return command_response(profile_sessions.revoke_others(request.user, request.session.session_key, request=request))
