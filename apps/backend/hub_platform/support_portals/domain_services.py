from __future__ import annotations

import uuid

import dns.exception
import dns.resolver
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from hub_platform.support_portals.addressing import normalize_domain, validate_domain
from hub_platform.support_portals.models import SupportPortal
from hub_platform.support_portals.statuses import PortalStatus


def domain_verification_name(portal: SupportPortal) -> str:
    return f"_custocrm.{portal.custom_domain}" if portal.custom_domain else ""


def domain_verification_value(portal: SupportPortal) -> str:
    return f"custocrm-verification={portal.custom_domain_verification_token}"


def set_custom_domain(portal: SupportPortal, value: str) -> SupportPortal:
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError(
            {"portal": "Восстановите портал, чтобы изменить его домен"}
        )
    normalized = normalize_domain(value)
    portal.custom_domain = validate_domain(normalized) if normalized else ""
    portal.custom_domain_verified_at = None
    portal.custom_domain_verification_token = uuid.uuid4()
    portal.full_clean()
    portal.save(
        update_fields=[
            "custom_domain",
            "custom_domain_verified_at",
            "custom_domain_verification_token",
            "updated_at",
        ]
    )
    return portal


def verify_custom_domain(portal: SupportPortal) -> SupportPortal:
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError(
            {"portal": "Восстановите портал, чтобы подтвердить его домен"}
        )
    if not portal.custom_domain:
        raise ValidationError({"customDomain": "Сначала укажите домен"})
    if settings.CUS_HELP_PUBLIC_IPV4:
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
        if settings.CUS_HELP_PUBLIC_IPV4 not in addresses:
            raise ValidationError(
                {"customDomain": "A-запись домена указывает не на сервер CustoCRM"}
            )

    expected = domain_verification_value(portal)
    try:
        answers = dns.resolver.resolve(domain_verification_name(portal), "TXT")
        values = {
            b"".join(answer.strings).decode("utf-8", errors="replace")
            for answer in answers
        }
    except (
        dns.resolver.NoAnswer,
        dns.resolver.NXDOMAIN,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ) as error:
        raise ValidationError(
            {"customDomain": "TXT-запись пока не найдена"}
        ) from error
    if expected not in values:
        raise ValidationError(
            {"customDomain": "TXT-запись не содержит код подтверждения"}
        )
    portal.custom_domain_verified_at = timezone.now()
    portal.full_clean()
    portal.save(update_fields=["custom_domain_verified_at", "updated_at"])
    return portal
