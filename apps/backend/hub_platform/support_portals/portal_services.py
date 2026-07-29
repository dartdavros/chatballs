from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hub_platform.channels.models import Channel
from hub_platform.identity.models import Department
from hub_platform.integrations.models import IntegrationProvider, IntegrationStatus
from hub_platform.products.models import Product
from hub_platform.subscriptions.keys import EntitlementKey, QuotaKey
from hub_platform.subscriptions.policy import require_entitlement
from hub_platform.subscriptions.usage_service import record_usage
from hub_platform.support_portals.addressing import hosted_domain
from hub_platform.support_portals.models import (
    SupportPortal,
    SupportPortalProduct,
)
from hub_platform.support_portals.statuses import PortalStatus
from hub_platform.tenancy.context import TenantContext


@dataclass(frozen=True)
class PortalInput:
    slug: str
    name: str
    default_locale: str = "ru"
    widget_channel_id: int | None = None


@transaction.atomic
def create_portal(*, context: TenantContext, data: PortalInput) -> SupportPortal:
    require_entitlement(context, EntitlementKey.SUPPORT_DEPARTMENT)
    support_department = Department.objects.get(
        organization=context.organization,
        code="support",
    )
    portal = SupportPortal(
        organization=context.organization,
        department=support_department,
        slug=data.slug.strip().lower(),
        hosted_domain=hosted_domain(data.slug.strip().lower()),
        name=data.name.strip(),
        default_locale=data.default_locale.strip().lower() or "ru",
        widget_channel=_widget_channel(context, data.widget_channel_id),
    )
    portal.full_clean()
    portal.save()
    record_usage(
        context=context,
        quota_key=QuotaKey.SUPPORT_PORTALS,
        quantity=1,
        idempotency_key=f"support-portal:{portal.public_id}:create",
        source="support_portal.created",
        aggregate_type="SupportPortal",
        aggregate_id=str(portal.public_id),
    )
    return portal


def update_portal(
    *, context: TenantContext, portal: SupportPortal, data: PortalInput
) -> SupportPortal:
    _check_tenant(context, portal)
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError({"portal": "Восстановите портал, чтобы изменить настройки"})
    portal.slug = data.slug.strip().lower()
    portal.hosted_domain = hosted_domain(portal.slug)
    portal.name = data.name.strip()
    portal.default_locale = data.default_locale.strip().lower() or "ru"
    portal.widget_channel = _widget_channel(context, data.widget_channel_id)
    portal.full_clean()
    portal.save()
    return portal


def _widget_channel(
    context: TenantContext,
    channel_id: int | None,
) -> Channel | None:
    if channel_id is None:
        return None
    try:
        return (
            Channel.objects.select_related("department")
            .filter(
                id=channel_id,
                organization=context.organization,
                department__code="support",
                is_active=True,
                requires_authenticated_product_identity=False,
                allow_anonymous_sessions=True,
                connections__provider=IntegrationProvider.WEB,
                connections__status=IntegrationStatus.OK,
                connections__is_active=True,
            )
            .distinct()
            .get()
        )
    except Channel.DoesNotExist as error:
        raise ValidationError(
            {"widgetChannelId": "Активный Web-виджет поддержки не найден"}
        ) from error


@transaction.atomic
def set_portal_status(
    *, context: TenantContext, portal: SupportPortal, status: str
) -> SupportPortal:
    _check_tenant(context, portal)
    if status not in PortalStatus.values:
        raise ValidationError({"status": "Неизвестный статус портала"})
    if status == portal.status:
        return portal
    portal.transition_version += 1
    if status == PortalStatus.ARCHIVED:
        record_usage(
            context=context,
            quota_key=QuotaKey.SUPPORT_PORTALS,
            quantity=-1,
            idempotency_key=f"support-portal:{portal.public_id}:archive:{portal.transition_version}",
            source="support_portal.archived",
            aggregate_type="SupportPortal",
            aggregate_id=str(portal.public_id),
        )
        portal.published_at = None
    elif portal.status == PortalStatus.ARCHIVED:
        require_entitlement(context, EntitlementKey.SUPPORT_DEPARTMENT)
        record_usage(
            context=context,
            quota_key=QuotaKey.SUPPORT_PORTALS,
            quantity=1,
            idempotency_key=f"support-portal:{portal.public_id}:restore:{portal.transition_version}",
            source="support_portal.restored",
            aggregate_type="SupportPortal",
            aggregate_id=str(portal.public_id),
        )
        status = PortalStatus.DRAFT
    elif status == PortalStatus.PUBLISHED:
        require_entitlement(context, EntitlementKey.SUPPORT_DEPARTMENT)
        portal.published_at = timezone.now()
    else:
        portal.published_at = None
    portal.status = status
    portal.save(update_fields=["status", "transition_version", "published_at", "updated_at"])
    return portal


@transaction.atomic
def replace_product_links(
    *, context: TenantContext, portal: SupportPortal, links: list[dict]
) -> SupportPortal:
    _check_tenant(context, portal)
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError(
            {"portal": "Восстановите портал, чтобы изменить его продукты"}
        )
    product_ids = [int(item.get("productId", 0)) for item in links]
    channel_ids = [
        int(item["supportChannelId"])
        for item in links
        if item.get("supportChannelId") is not None
    ]
    if len(product_ids) != len(set(product_ids)):
        raise ValidationError({"products": "Один продукт нельзя добавить дважды"})
    products = {
        item.id: item
        for item in Product.objects.filter(
            organization=context.organization,
            id__in=product_ids,
        )
    }
    channels = {
        item.id: item
        for item in Channel.objects.select_related("department").filter(
            organization=context.organization,
            id__in=channel_ids,
        )
    }
    if len(products) != len(product_ids) or len(channels) != len(channel_ids):
        raise ValidationError({"products": "Продукт или канал поддержки не найден"})
    replacements = []
    for position, item in enumerate(links):
        channel_id = item.get("supportChannelId")
        link = SupportPortalProduct(
            organization=context.organization,
            portal=portal,
            product=products[int(item["productId"])],
            support_channel=channels.get(int(channel_id)) if channel_id is not None else None,
            sort_order=int(item.get("sortOrder", position)),
        )
        link.full_clean()
        replacements.append(link)
    portal.product_links.all().delete()
    SupportPortalProduct.objects.bulk_create(replacements)
    return portal


def _check_tenant(context: TenantContext, portal: SupportPortal) -> None:
    if portal.organization_id != context.organization_id:
        raise ValidationError({"portal": "Портал принадлежит другой организации"})
    if portal.department.code != "support":
        raise ValidationError({"portal": "Портал не относится к отделу поддержки"})
