"""API сервисных подключений (SPEC-0037 R-1, R-7; C4 code-service-connection-service).

Просмотр — ``integrations.view``, изменения — ``integrations.manage``
(владелец и администратор организации). Вьюхи с сетевой проверкой сами
управляют транзакцией: запрос к сервису не держит соединение с базой.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.deletion import IntegrationInUse
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.integrations.service_connections import services
from chatballs.integrations.service_connections.binding import ServiceUnavailable, load_lookup
from chatballs.integrations.service_connections.errors import ServiceCheckFailed, error_payload
from chatballs.integrations.service_connections.payloads import catalog_payload, connection_payload
from chatballs.tenancy.database import tenant_atomic


class ServiceAPIView(APIView):
    """Вьюха с сетевым запросом сама открывает транзакции, поэтому и право
    проверяется внутри контекста организации: без него RLS скрывает членство."""

    permission_classes = [HasCapability]
    tenant_manages_own_transaction = True

    def check_permissions(self, request: Request) -> None:
        with tenant_atomic(request.tenant_context):
            super().check_permissions(request)


def _connections(request: Request):
    return Integration.objects.select_related("service_settings").filter(
        organization_id=request.tenant_context.organization_id, provider=IntegrationProvider.ADAPTER
    )


def connection_for(request: Request, connection_id: int) -> Integration | None:
    with tenant_atomic(request.tenant_context):
        return _connections(request).filter(id=connection_id).first()


def access_input(request: Request) -> services.AccessInput:
    data = request.data if isinstance(request.data, dict) else {}
    values = data.get("values")
    return services.AccessInput(
        adapter_key=str(data.get("adapter", "")),
        auth_method=str(data.get("authMethod", "")),
        values=values if isinstance(values, dict) else {},
        name=str(data.get("name", "")),
    )


def invalid(error: ValidationError) -> Response:
    errors = error.message_dict if hasattr(error, "message_dict") else {"detail": error.messages}
    detail = "; ".join(message for messages in errors.values() for message in messages)
    return Response({"detail": detail, "errors": errors}, status=400)


def _check_failed(adapter_key: str, failure: ServiceCheckFailed) -> Response:
    adapter = default_registry().adapter(adapter_key)
    return Response({"error": error_payload(adapter, failure.code).as_dict()}, status=400)


def _audit(request: Request, action: str, integration_id: int, payload: dict | None = None) -> None:
    # В журнал — только идентификаторы и ключ адаптера, никаких значений доступа.
    record_audit_event(
        action=action,
        actor=request.user,
        organization=request.tenant_context.organization,
        object_type="Integration",
        object_id=str(integration_id),
        payload=payload or {},
        request=request,
    )


def not_found() -> Response:
    return Response({"detail": t("services.not_found")}, status=404)


class ServiceAdapterListView(APIView):
    permission_classes = [HasCapability]
    required_capability = "integrations.view"

    def get(self, request: Request) -> Response:
        return Response({"items": catalog_payload()})


class ServiceConnectionListView(ServiceAPIView):
    required_capabilities = {"GET": "integrations.view", "POST": "integrations.manage"}

    def get(self, request: Request) -> Response:
        with tenant_atomic(request.tenant_context):
            items = [connection_payload(item) for item in _connections(request).order_by("name")]
        return Response({"items": items})

    def post(self, request: Request) -> Response:
        data = access_input(request)
        try:
            integration = services.create_connection(context=request.tenant_context, data=data)
        except ValidationError as error:
            return invalid(error)
        except ServiceCheckFailed as failure:
            return _check_failed(data.adapter_key, failure)
        with tenant_atomic(request.tenant_context):
            _audit(request, "integrations.service_connected", integration.id, {"adapter": data.adapter_key})
            payload = connection_payload(integration)
        return Response({"connection": payload}, status=201)


class ServiceConnectionDetailView(ServiceAPIView):
    required_capabilities = {"GET": "integrations.view", "PATCH": "integrations.manage", "DELETE": "integrations.manage"}

    def get(self, request: Request, connection_id: int) -> Response:
        integration = connection_for(request, connection_id)
        if integration is None:
            return not_found()
        with tenant_atomic(request.tenant_context):
            return Response({"connection": connection_payload(integration)})

    def patch(self, request: Request, connection_id: int) -> Response:
        integration = connection_for(request, connection_id)
        if integration is None:
            return not_found()
        data = request.data if isinstance(request.data, dict) else {}
        context = request.tenant_context
        try:
            if "name" in data:
                services.rename_connection(context=context, integration=integration, name=str(data["name"]))
                with tenant_atomic(context):
                    _audit(request, "integrations.service_renamed", integration.id)
            if isinstance(data.get("isActive"), bool):
                services.set_active(context=context, integration=integration, active=data["isActive"])
                action = "integrations.service_resumed" if data["isActive"] else "integrations.service_paused"
                with tenant_atomic(context):
                    _audit(request, action, integration.id)
        except ValidationError as error:
            return invalid(error)
        with tenant_atomic(context):
            return Response({"connection": connection_payload(integration)})

    def delete(self, request: Request, connection_id: int) -> Response:
        integration = connection_for(request, connection_id)
        if integration is None:
            return not_found()
        try:
            services.delete_connection(context=request.tenant_context, integration=integration)
        except IntegrationInUse as error:
            return Response({"detail": str(error)}, status=409)
        with tenant_atomic(request.tenant_context):
            _audit(request, "integrations.service_deleted", connection_id)
        return Response(status=204)


class ServiceConnectionCheckView(ServiceAPIView):
    required_capability = "integrations.manage"

    def post(self, request: Request, connection_id: int) -> Response:
        integration = connection_for(request, connection_id)
        if integration is None:
            return not_found()
        inputs = request.data.get("inputs") if isinstance(request.data, dict) else None
        try:
            services.check_connection(
                context=request.tenant_context, integration=integration, inputs=inputs if isinstance(inputs, dict) else None
            )
            failure = None
        except ServiceCheckFailed as error:
            failure = error
        with tenant_atomic(request.tenant_context):
            _audit(request, "integrations.service_checked", integration.id, {"ok": failure is None})
            payload = connection_payload(integration)
        if failure is not None:
            return Response({"connection": payload, **_check_failed(integration.service_settings.adapter_key, failure).data}, status=400)
        return Response({"connection": payload})


class ServiceConnectionAccessView(ServiceAPIView):
    required_capability = "integrations.manage"

    def post(self, request: Request, connection_id: int) -> Response:
        integration = connection_for(request, connection_id)
        if integration is None:
            return not_found()
        values = request.data.get("values") if isinstance(request.data, dict) else None
        try:
            services.replace_access(
                context=request.tenant_context, integration=integration, values=values if isinstance(values, dict) else {}
            )
        except ValidationError as error:
            return invalid(error)
        except ServiceCheckFailed as failure:
            return _check_failed(integration.service_settings.adapter_key, failure)
        with tenant_atomic(request.tenant_context):
            _audit(request, "integrations.service_access_replaced", integration.id)
            return Response({"connection": connection_payload(integration)})


class ServiceLookupView(ServiceAPIView):
    required_capability = "integrations.manage"

    def get(self, request: Request, connection_id: int, key: str) -> Response:
        integration = connection_for(request, connection_id)
        if integration is None:
            return not_found()
        try:
            items = load_lookup(tenant=request.tenant_context, integration=integration, key=key)
        except ServiceUnavailable as error:
            adapter = default_registry().adapter(integration.service_settings.adapter_key)
            return Response({"error": error_payload(adapter, error.code).as_dict()}, status=400)
        return Response({"items": [{"value": item.value, "label": item.label} for item in items]})
