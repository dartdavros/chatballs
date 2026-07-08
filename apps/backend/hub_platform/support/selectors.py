from __future__ import annotations

from django.db.models import QuerySet

from hub_platform.support.models import (
    ContractStatus,
    ProductSupportContract,
    SupportIdentitySnapshot,
)


def contracts_for_organization(organization_id: int) -> QuerySet[ProductSupportContract]:
    return (
        ProductSupportContract.objects.filter(organization_id=organization_id)
        .select_related("product")
        .prefetch_related("allowed_channels")
        .order_by("code")
    )


def contract_for_organization(
    *, organization_id: int, contract_id: int
) -> ProductSupportContract:
    return contracts_for_organization(organization_id).get(id=contract_id)


def contract_by_code(*, organization_id: int, code: str) -> ProductSupportContract | None:
    """Контракт по code (любой статус) — для различения CONTRACT_NOT_FOUND/DISABLED."""
    return (
        ProductSupportContract.objects.filter(
            organization_id=organization_id, code=code
        )
        .select_related("product")
        .first()
    )


def active_contract_for(*, organization_id: int, code: str) -> ProductSupportContract | None:
    """Контракт, принимающий production traffic: ACTIVE или DEPRECATED (migration window)."""
    return (
        ProductSupportContract.objects.filter(
            organization_id=organization_id, code=code
        )
        .filter(status__in=[ContractStatus.ACTIVE, ContractStatus.DEPRECATED])
        .select_related("product")
        .first()
    )


def snapshots_for_subject(
    *, product_id: int, subject_key: str
) -> QuerySet[SupportIdentitySnapshot]:
    return (
        SupportIdentitySnapshot.objects.filter(product_id=product_id, subject_key=subject_key)
        .order_by("-verified_at")
    )
