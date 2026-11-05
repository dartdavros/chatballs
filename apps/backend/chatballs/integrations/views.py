from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.deletion import IntegrationInUse, delete_integration
from chatballs.integrations.external_tools import refresh_tools
from chatballs.integrations.models import Integration
from chatballs.integrations.operator_routes import UNSET_GROUP
from chatballs.integrations.read_only import confirm_read_only, revoke_read_only
from chatballs.integrations.selectors import (
    integration_for_context,
    integrations_for_context,
)
from chatballs.integrations.serializers import integration_payload, restore_proxy_password
from chatballs.integrations.services import (
    IntegrationInput,
    create_integration,
    test_integration,
    update_integration,
)


def _input(body: dict[str, object], *, current: Integration | None = None) -> IntegrationInput:
    config = body.get("config", current.config if current else {})
    config = _keep_proxy_password(config, current)
    raw_channel = body.get("channelId", current.channel_id if current else None)
    channel_id = int(raw_channel) if isinstance(raw_channel, int) or (isinstance(raw_channel, str) and raw_channel.isdigit()) else None
    return IntegrationInput(
        provider=str(body.get("provider", current.provider if current else "")),
        name=str(body.get("name", current.name if current else "")),
        secret=body.get("secret") if "secret" in body else None,
        config=config if isinstance(config, dict) else {},
        channel_id=channel_id,
        is_active=(
            body["isActive"]
            if isinstance(body.get("isActive"), bool)
            else (current.is_active if current else None)
        ),
        external=body.get("externalServer"),
        group_id=body.get("groupId", UNSET_GROUP),
    )


def _keep_proxy_password(config: object, current: Integration | None) -> object:
    """Маска пароля прокси из ответа не должна затирать настоящий пароль."""
    if not isinstance(config, dict) or current is None:
        return config
    submitted = str(config.get("proxyUrl", config.get("proxy_url", "")) or "")
    if not submitted:
        return config
    restored = restore_proxy_password(submitted, str(current.config.get("proxy_url", "")))
    if restored == submitted:
        return config
    config = dict(config)
    config.pop("proxy_url", None)
    config["proxyUrl"] = restored
    return config


def _validation_error(error: Exception) -> Response:
    if isinstance(error, ValidationError):
        if hasattr(error, "message_dict"):
            detail = "; ".join(message for messages in error.message_dict.values() for message in messages)
            # По полям — для формы, которая показывает все ошибки сразу.
            return Response({"detail": detail, "errors": error.message_dict}, status=400)
        else:
            detail = "; ".join(error.messages)
    else:
        detail = "Интеграция с таким именем уже существует"
    return Response({"detail": detail}, status=400)


def _audit(
    request: Request,
    action: str,
    integration: Integration,
    *,
    object_id: int | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    record_audit_event(
        action=action,
        actor=request.user,
        organization=request.tenant_context.organization,
        object_type="Integration",
        object_id=str(integration.id if object_id is None else object_id),
        payload=payload,
        request=request,
    )


class IntegrationListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "integrations.view", "POST": "integrations.manage"}

    def get(self, request: Request) -> Response:
        items = integrations_for_context(request.tenant_context)
        return Response({"items": [integration_payload(item) for item in items]})

    def post(self, request: Request) -> Response:
        try:
            integration = create_integration(
                context=request.tenant_context, data=_input(request.data)
            )
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        _audit(request, "integrations.integration_created", integration)
        return Response({"integration": integration_payload(integration)}, status=201)


class IntegrationDetailView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"

    def _get(self, request: Request, integration_id: int) -> Integration:
        return integration_for_context(
            context=request.tenant_context, integration_id=integration_id
        )

    def patch(self, request: Request, integration_id: int) -> Response:
        try:
            integration = self._get(request, integration_id)
            integration = update_integration(
                context=request.tenant_context,
                integration=integration,
                data=_input(request.data, current=integration),
            )
        except Integration.DoesNotExist:
            return Response({"detail": t("settings.integration_not_found")}, status=404)
        except (ValidationError, IntegrityError) as error:
            return _validation_error(error)
        _audit(request, "integrations.integration_updated", integration)
        return Response({"integration": integration_payload(integration)})

    def delete(self, request: Request, integration_id: int) -> Response:
        try:
            integration = self._get(request, integration_id)
        except Integration.DoesNotExist:
            return Response({"detail": t("settings.integration_not_found")}, status=404)
        integration_id = integration.id
        try:
            delete_integration(context=request.tenant_context, integration=integration)
        except IntegrationInUse as error:
            return Response({"detail": str(error)}, status=409)
        _audit(
            request,
            "integrations.integration_deleted",
            integration,
            object_id=integration_id,
        )
        return Response(status=204)


class IntegrationTestView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"
    tenant_manages_own_transaction = True

    def check_permissions(self, request: Request) -> None:
        from chatballs.tenancy.database import tenant_atomic

        with tenant_atomic(request.tenant_context):
            super().check_permissions(request)

    def post(self, request: Request, integration_id: int) -> Response:
        from chatballs.speech.checking import finish_check, prepare_check, run_check
        from chatballs.tenancy.database import tenant_atomic

        context = request.tenant_context
        with tenant_atomic(context):
            try:
                integration = integration_for_context(context=context, integration_id=integration_id)
            except Integration.DoesNotExist:
                return Response({"detail": t("settings.integration_not_found")}, status=404)
            if integration.provider != "YANDEX_SPEECHKIT":
                try:
                    integration = test_integration(context=context, integration=integration)
                except ValidationError as error:
                    return _validation_error(error)
                _audit(request, "integrations.integration_tested", integration)
                return Response({"integration": integration_payload(integration)})
            job = prepare_check(integration, request.data.get("capability", "stt"))
        error_code = run_check(job)
        with tenant_atomic(context):
            try:
                integration = finish_check(context, job, error_code)
            except ValidationError as error:
                return _validation_error(error)
            _audit(request, "integrations.integration_tested", integration)
            return Response({"integration": integration_payload(integration)})


class IntegrationToolsRefreshView(APIView):
    """«Обновить список инструментов» MCP-сервера: неудача — не ошибка запроса,
    а состояние сервера в ответе, как у проверки соединения."""

    permission_classes = [HasCapability]
    required_capability = "integrations.manage"

    def post(self, request: Request, integration_id: int) -> Response:
        try:
            integration = integration_for_context(
                context=request.tenant_context, integration_id=integration_id
            )
            integration = refresh_tools(context=request.tenant_context, integration=integration)
        except Integration.DoesNotExist:
            return Response({"detail": t("settings.integration_not_found")}, status=404)
        except ValidationError as error:
            return _validation_error(error)
        _audit(request, "integrations.tools_refreshed", integration)
        return Response({"integration": integration_payload(integration)})


class _ToolReadOnlyView(APIView):
    """Подтверждение «только читает» для MCP-инструмента и его снятие."""

    permission_classes = [HasCapability]
    required_capability = "integrations.manage"
    audit_action: str

    def apply(self, request: Request, integration: Integration, name: object) -> None:
        raise NotImplementedError

    def post(self, request: Request, integration_id: int) -> Response:
        body = request.data if isinstance(request.data, dict) else {}
        name = body.get("name")
        try:
            integration = integration_for_context(
                context=request.tenant_context, integration_id=integration_id
            )
            self.apply(request, integration, name)
        except Integration.DoesNotExist:
            return Response({"detail": t("settings.integration_not_found")}, status=404)
        except ValidationError as error:
            return _validation_error(error)
        _audit(request, self.audit_action, integration, payload={"tool": name})
        return Response({"integration": integration_payload(integration)})


class IntegrationToolConfirmView(_ToolReadOnlyView):
    audit_action = "integrations.tool_read_only_confirmed"

    def apply(self, request: Request, integration: Integration, name: object) -> None:
        confirm_read_only(
            context=request.tenant_context,
            integration=integration,
            name=name,
            confirmed=request.data.get("confirmed"),
            actor=request.user,
        )


class IntegrationToolRevokeView(_ToolReadOnlyView):
    audit_action = "integrations.tool_read_only_revoked"

    def apply(self, request: Request, integration: Integration, name: object) -> None:
        revoke_read_only(
            context=request.tenant_context, integration=integration, name=name, actor=request.user
        )
