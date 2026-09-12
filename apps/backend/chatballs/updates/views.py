"""Обновления установки в интерфейсе: состояние, проверка, установка.

Читает менеджер любой организации (баннер показывается только администратору
установки, но версия видна всем менеджерам в «Платформе»), проверять канал и
запускать установку может только администратор установки.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.identity.audit import record_audit_event
from chatballs.identity.instance_access import InstanceSettingsPermission, IsInstanceAdmin
from chatballs.updates.models import UpdateState
from chatballs.updates.services import (
    InstallNotPossible,
    check_for_updates,
    request_install,
    sync_install_status,
    update_payload,
)


class UpdateStateView(APIView):
    permission_classes = [InstanceSettingsPermission]

    def get(self, request: Request) -> Response:
        state = sync_install_status(UpdateState.load())
        return Response({"update": update_payload(state)})


class UpdateCheckView(APIView):
    permission_classes = [IsInstanceAdmin]

    def post(self, request: Request) -> Response:
        state = sync_install_status(check_for_updates(force=True))
        return Response({"update": update_payload(state)})


class UpdateInstallView(APIView):
    permission_classes = [IsInstanceAdmin]

    def post(self, request: Request) -> Response:
        try:
            state = request_install(actor=request.user)
        except InstallNotPossible as error:
            return Response({"detail": str(error), "code": error.code}, status=409)
        record_audit_event(
            action="updates.install_requested",
            actor=request.user,
            organization=None,
            object_type="UpdateState",
            object_id=state.install_version,
            payload={"version": state.install_version},
            request=request,
        )
        return Response({"update": update_payload(state)}, status=202)
