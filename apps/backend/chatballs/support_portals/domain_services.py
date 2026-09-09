from __future__ import annotations

import dns.exception
import dns.resolver
from django.core.exceptions import ValidationError
from django.utils import timezone

from chatballs.support_portals.addressing import normalize_domain, validate_domain
from chatballs.support_portals.models import SupportPortal
from chatballs.support_portals.public_address import help_public_ipv4
from chatballs.support_portals.statuses import PortalStatus


def set_custom_domain(portal: SupportPortal, value: str) -> SupportPortal:
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError(
            {"portal": "Восстановите портал, чтобы изменить его домен"}
        )
    normalized = normalize_domain(value)
    portal.custom_domain = validate_domain(normalized) if normalized else ""
    portal.custom_domain_verified_at = None
    portal.full_clean()
    portal.save(
        update_fields=["custom_domain", "custom_domain_verified_at", "updated_at"]
    )
    return portal


def verify_custom_domain(portal: SupportPortal) -> SupportPortal:
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError(
            {"portal": "Восстановите портал, чтобы подтвердить его домен"}
        )
    if not portal.custom_domain:
        raise ValidationError({"customDomain": "Сначала укажите домен"})
    # Подтверждать владение доменом нечем и незачем: продукт self-hosted, домен
    # и установка принадлежат одному владельцу (README дизайн-базлайна, решение
    # 6). Остаётся техническая проверка «ведёт ли домен на этот сервер» — она
    # нужна, чтобы выписать сертификат.
    server_ipv4 = help_public_ipv4()
    if server_ipv4:
        try:
            address_answers = dns.resolver.resolve(portal.custom_domain, "A")
            addresses = {
                getattr(answer, "address", str(answer).rstrip("."))
                for answer in address_answers
            }
        except (
            dns.resolver.NoAnswer,
            dns.resolver.NXDOMAIN,
            dns.resolver.NoNameservers,
            dns.exception.Timeout,
        ) as error:
            raise ValidationError(
                {"customDomain": "A-запись домена пока не найдена"}
            ) from error
        if server_ipv4 not in addresses:
            raise ValidationError(
                {"customDomain": "A-запись домена указывает не на сервер Chatballs"}
            )

    portal.custom_domain_verified_at = timezone.now()
    portal.full_clean()
    portal.save(update_fields=["custom_domain_verified_at", "updated_at"])
    return portal
