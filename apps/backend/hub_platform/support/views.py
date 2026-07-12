from django.core.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import IsManager
from hub_platform.channels.models import Channel
from hub_platform.conversations.models import Conversation
from hub_platform.conversations.serializers import conversation_payload
from hub_platform.identity.audit import record_audit_event
from hub_platform.support import errors
from hub_platform.support.messages import post_support_message, support_messages_since
from hub_platform.support.models import ProductSupportContract
from hub_platform.support.selectors import contract_for_organization, contracts_for_organization
from hub_platform.support.serializers import (
    support_contract_payload,
    support_identity_snapshot_payload,
)
from hub_platform.support.services import ContractInput, register_contract, set_contract_status
from hub_platform.support.session import start_support_session
from hub_platform.support.widget_credential import verify_widget_credential


def _validation_error(error: ValidationError) -> Response:
    detail = (
        "; ".join(m for ms in error.message_dict.values() for m in ms)
        if hasattr(error, "message_dict")
        else "; ".join(error.messages)
    )
    return Response({"detail": detail}, status=400)


class _Public(APIView):
    # Продукт → Hub: нет пользовательской сессии Django, нет CSRF.
    authentication_classes: list = []
    permission_classes = [AllowAny]


class _ManagerBase(APIView):
    permission_classes = [IsManager]

    def _org(self, request: Request):
        return request.user.employee_profile.organization


class SupportContractListView(_ManagerBase):
    def get(self, request: Request) -> Response:
        contracts = contracts_for_organization(self._org(request).id)
        return Response({"items": [support_contract_payload(c) for c in contracts]})

    def post(self, request: Request) -> Response:
        org = self._org(request)
        try:
            data = ContractInput(
                code=str(request.data.get("code", "")),
                product_id=int(request.data.get("productId", 0)),
                status=str(request.data.get("status", "")) or "DRAFT",
                schema_json=request.data.get("schema_json") or request.data.get("schemaJson") or {},
                identity_mapping_json=request.data.get("identity_mapping_json")
                or request.data.get("identityMappingJson")
                or {},
                operator_ui_json=request.data.get("operator_ui_json")
                or request.data.get("operatorUiJson")
                or {},
                ai_context_json=request.data.get("ai_context_json")
                or request.data.get("aiContextJson")
                or {},
                search_mapping_json=request.data.get("search_mapping_json")
                or request.data.get("searchMappingJson")
                or {},
                sensitive_fields_json=request.data.get("sensitive_fields_json")
                or request.data.get("sensitiveFieldsJson")
                or {},
                allowed_channel_ids=tuple(
                    int(x) for x in (request.data.get("allowedChannelIds") or [])
                ),
            )
        except (TypeError, ValueError):
            return Response({"detail": "Invalid contract payload"}, status=400)
        try:
            contract = register_contract(organization=org, data=data)
        except ValidationError as error:
            return _validation_error(error)
        record_audit_event(
            action="support.contract_registered",
            actor=request.user,
            organization=org,
            object_type="ProductSupportContract",
            object_id=str(contract.id),
            request=request,
        )
        return Response({"contract": support_contract_payload(contract)}, status=201)


class SupportContractDetailView(_ManagerBase):
    def get(self, request: Request, contract_id: int) -> Response:
        try:
            contract = contract_for_organization(
                organization_id=self._org(request).id, contract_id=contract_id
            )
        except ProductSupportContract.DoesNotExist:
            return Response({"detail": "Контракт не найден"}, status=404)
        return Response({"contract": support_contract_payload(contract)})


class SupportContractStatusView(_ManagerBase):
    def post(self, request: Request, contract_id: int) -> Response:
        try:
            contract = contract_for_organization(
                organization_id=self._org(request).id, contract_id=contract_id
            )
        except ProductSupportContract.DoesNotExist:
            return Response({"detail": "Контракт не найден"}, status=404)
        status = str(request.data.get("status", ""))
        try:
            contract = set_contract_status(contract=contract, status=status)
        except ValidationError as error:
            return _validation_error(error)
        record_audit_event(
            action=f"support.contract_{status.lower()}",
            actor=request.user,
            organization=self._org(request),
            object_type="ProductSupportContract",
            object_id=str(contract.id),
            request=request,
        )
        return Response({"contract": support_contract_payload(contract)})


class SupportSessionStartView(_Public):
    def post(self, request: Request) -> Response:
        channel_code = str(request.data.get("channel", "")).strip()
        token = str(request.data.get("token", ""))
        if not channel_code or not token:
            return _denied()
        channel = Channel.objects.select_related("department", "product", "organization").filter(
            code=channel_code
        ).first()
        if channel is None:
            return _denied()
        try:
            result = start_support_session(channel=channel, token=token, request=request)
        except errors.SupportSessionError:
            # Audit DENIED уже записан в сервисе; публичный ответ безопасный.
            return _denied()
        return Response(
            {
                "conversation": conversation_payload(result["conversation"], with_messages=True),
                "snapshot": support_identity_snapshot_payload(result["snapshot"]),
                "widgetCredential": result["widget_credential"],
            },
            status=201,
        )


def _resolve_widget_conversation(request: Request) -> Conversation | None:
    """Возвращает conversation по widget-credential (Authorization: Bearer) или None."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    claims = verify_widget_credential(auth[7:])
    if claims is None:
        return None
    conversation = (
        Conversation.objects.select_related("channel", "support_identity_snapshot")
        .filter(id=claims["conversation_id"], support_identity_snapshot_id=claims["snapshot_id"])
        .first()
    )
    return conversation


class SupportSessionMessagesView(_Public):
    # Polling (GET) и отправка (POST) сообщений support-диалога виджетом.
    # Авторизация — stateless widget-credential (Bearer), выданный при старте сессии.
    def get(self, request: Request) -> Response:
        conversation = _resolve_widget_conversation(request)
        if conversation is None:
            return Response({"detail": "Сессия не найдена"}, status=401)
        try:
            since = int(request.GET.get("since", "0") or 0)
        except ValueError:
            since = 0
        return Response(support_messages_since(conversation, since))

    def post(self, request: Request) -> Response:
        conversation = _resolve_widget_conversation(request)
        if conversation is None:
            return Response({"detail": "Сессия не найдена"}, status=401)
        text = str(request.data.get("text", "")).strip()
        if not text:
            return Response({"detail": "Пустое сообщение"}, status=400)
        post_support_message(conversation=conversation, text=text[:4000])
        return Response({"ok": True}, status=201)


class SupportSnapshotsBySubjectView(APIView):
    # История обращений клиента для правой панели оператора (этап 1 — минимально).
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from hub_platform.support.selectors import snapshots_for_subject

        product_code = request.query_params.get("product")
        subject_key = request.query_params.get("subject")
        if not product_code or not subject_key:
            return Response({"detail": "product и subject обязательны"}, status=400)
        from hub_platform.products.models import Product

        product = Product.objects.filter(
            organization=request.user.employee_profile.organization, code=product_code
        ).first()
        if product is None:
            return Response({"detail": "Продукт не найден"}, status=404)
        snapshots = snapshots_for_subject(product_id=product.id, subject_key=subject_key)[:20]
        return Response({"items": [support_identity_snapshot_payload(s) for s in snapshots]})


def _denied() -> Response:
    return Response(
        {"error": "support_unavailable", "message": errors.PUBLIC_SUPPORT_UNAVAILABLE},
        status=422,
    )
