from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.channels.models import Channel
from hub_platform.identity.models import Organization
from hub_platform.products.models import Product
from hub_platform.support.models import ContractStatus, ProductSupportContract


@dataclass(frozen=True)
class ContractInput:
    code: str
    product_id: int
    status: str = ContractStatus.DRAFT
    schema_json: dict = None  # type: ignore[assignment]
    identity_mapping_json: dict = None  # type: ignore[assignment]
    operator_ui_json: dict = None  # type: ignore[assignment]
    ai_context_json: dict = None  # type: ignore[assignment]
    search_mapping_json: dict = None  # type: ignore[assignment]
    sensitive_fields_json: dict = None  # type: ignore[assignment]
    allowed_channel_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        # None → dict, чтобы JSONField(default=dict) был согласован.
        for f in (
            "schema_json",
            "identity_mapping_json",
            "operator_ui_json",
            "ai_context_json",
            "search_mapping_json",
            "sensitive_fields_json",
        ):
            if getattr(self, f) is None:
                object.__setattr__(self, f, {})


def _resolve_channels(organization: Organization, ids: tuple[int, ...]) -> list[Channel]:
    if not ids:
        return []
    channels = list(Channel.objects.filter(organization=organization, id__in=ids))
    if len(channels) != len(set(ids)):
        raise ValidationError({"allowedChannelIds": "Channel not found"})
    return channels


@transaction.atomic
def register_contract(
    *, organization: Organization, data: ContractInput
) -> ProductSupportContract:
    try:
        product = Product.objects.get(id=data.product_id, organization=organization)
    except Product.DoesNotExist as error:
        raise ValidationError({"productId": "Product not found"}) from error
    contract = ProductSupportContract(
        organization=organization,
        product=product,
        code=data.code.strip().lower(),
        version=_version_from_code(data.code),
        status=data.status,
        schema_json=data.schema_json,
        identity_mapping_json=data.identity_mapping_json,
        operator_ui_json=data.operator_ui_json,
        ai_context_json=data.ai_context_json,
        search_mapping_json=data.search_mapping_json,
        sensitive_fields_json=data.sensitive_fields_json,
    )
    contract.full_clean()
    contract.save()
    for channel in _resolve_channels(organization, data.allowed_channel_ids):
        contract.allowed_channels.add(channel)
    return contract


def set_contract_status(*, contract: ProductSupportContract, status: str) -> ProductSupportContract:
    if status not in ContractStatus.values:
        raise ValidationError({"status": "Unknown contract status"})
    if contract.status != status:
        contract.status = status
        contract.save(update_fields=["status", "updated_at"])
    return contract


def _version_from_code(code: str) -> int:
    # <product_code>.support.v<major>; clean() дополнительно валидирует формат.
    tail = code.strip().lower().rsplit(".v", 1)[-1]
    if not tail.isdigit():
        raise ValidationError({"code": "Contract code must end with .v<major>"})
    return int(tail)
