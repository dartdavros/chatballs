from django.core.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.identity.audit import record_audit_event
from chatballs.support.models import ProductSupportContract
from chatballs.support.selectors import contract_for_context, contracts_for_context
from chatballs.support.serializers import (
    support_contract_payload,
    support_identity_snapshot_payload,
)
from chatballs.support.services import ContractInput, register_contract, set_contract_status


def _validation_error(error: ValidationError) -> Response:
    detail = (
        "; ".join(m for ms in error.message_dict.values() for m in ms)
        if hasattr(error, "message_dict")
        else "; ".join(error.messages)
    )
    return Response({"detail": detail}, status=400)


class _ManagerBase(APIView):
    permission_classes = [HasCapability]
    required_capability = "products.manage"
    require_organization_scope = True

    def _org(self, request: Request):
        return request.tenant_context.organization


class SupportContractListView(_ManagerBase):
    def get(self, request: Request) -> Response:
        contracts = contracts_for_context(request.tenant_context)
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
            contract = register_contract(context=request.tenant_context, data=data)
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
            contract = contract_for_context(
                context=request.tenant_context, contract_id=contract_id
            )
        except ProductSupportContract.DoesNotExist:
            return Response({"detail": "Контракт не найден"}, status=404)
        return Response({"contract": support_contract_payload(contract)})


class SupportContractStatusView(_ManagerBase):
    def post(self, request: Request, contract_id: int) -> Response:
        try:
            contract = contract_for_context(
                context=request.tenant_context, contract_id=contract_id
            )
        except ProductSupportContract.DoesNotExist:
            return Response({"detail": "Контракт не найден"}, status=404)
        status = str(request.data.get("status", ""))
        try:
            contract = set_contract_status(
                context=request.tenant_context, contract=contract, status=status
            )
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


class SupportSnapshotsBySubjectView(APIView):
    # История обращений клиента для правой панели оператора (этап 1 — минимально).
    permission_classes = [HasCapability]
    required_capability = "support.view"

    def get(self, request: Request) -> Response:
        from chatballs.support.selectors import snapshots_for_subject

        product_code = request.query_params.get("product")
        subject_key = request.query_params.get("subject")
        if not product_code or not subject_key:
            return Response({"detail": "product и subject обязательны"}, status=400)
        from chatballs.products.models import Product

        product = Product.objects.filter(
            organization=request.tenant_context.organization, code=product_code
        ).first()
        if product is None:
            return Response({"detail": "Продукт не найден"}, status=404)
        snapshots = snapshots_for_subject(
            context=request.tenant_context,
            product_id=product.id,
            subject_key=subject_key,
        )
        snapshots = snapshots[:20]
        return Response({"items": [support_identity_snapshot_payload(s) for s in snapshots]})
