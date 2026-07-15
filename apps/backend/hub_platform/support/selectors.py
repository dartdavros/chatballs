from __future__ import annotations

from django.db.models import QuerySet

from hub_platform.support.models import (
    ContractStatus,
    ProductSupportContract,
    SupportIdentitySnapshot,
)
from hub_platform.tenancy.context import TenantContext


def contracts_for_context(context: TenantContext) -> QuerySet[ProductSupportContract]:
    return (
        ProductSupportContract.objects.filter(organization_id=context.organization_id)
        .select_related("product")
        .prefetch_related("allowed_channels")
        .order_by("code")
    )


def contract_for_context(
    *, context: TenantContext, contract_id: int
) -> ProductSupportContract:
    return contracts_for_context(context).get(id=contract_id)


def contract_by_code(*, context: TenantContext, code: str) -> ProductSupportContract | None:
    """Контракт по code (любой статус) — для различения CONTRACT_NOT_FOUND/DISABLED."""
    return (
        ProductSupportContract.objects.filter(
            organization_id=context.organization_id, code=code
        )
        .select_related("product")
        .first()
    )


def active_contract_for(*, context: TenantContext, code: str) -> ProductSupportContract | None:
    """Контракт, принимающий production traffic: ACTIVE или DEPRECATED (migration window)."""
    return (
        ProductSupportContract.objects.filter(
            organization_id=context.organization_id, code=code
        )
        .filter(status__in=[ContractStatus.ACTIVE, ContractStatus.DEPRECATED])
        .select_related("product")
        .first()
    )


def snapshots_for_subject(
    *, context: TenantContext, product_id: int, subject_key: str
) -> QuerySet[SupportIdentitySnapshot]:
    return (
        SupportIdentitySnapshot.objects.filter(
            organization_id=context.organization_id,
            product_id=product_id,
            subject_key=subject_key,
        )
        .order_by("-verified_at")
    )
