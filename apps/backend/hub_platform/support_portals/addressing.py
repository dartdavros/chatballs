from __future__ import annotations

import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


HOST_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_domain(value: str) -> str:
    return value.strip().lower().rstrip(".")


def validate_domain(value: str) -> str:
    domain = normalize_domain(value)
    if not domain or len(domain) > 253:
        raise ValidationError("Некорректное доменное имя")
    labels = domain.split(".")
    if len(labels) < 2 or any(not HOST_LABEL_RE.fullmatch(label) for label in labels):
        raise ValidationError("Некорректное доменное имя")
    return domain


def hosted_domain(portal_key: str) -> str:
    base_domain = normalize_domain(settings.CUS_HELP_BASE_DOMAIN)
    return validate_domain(f"{portal_key}.{base_domain}")


def clean_portal_domains(portal) -> None:
    portal.slug = portal.slug.strip().lower()
    portal.hosted_domain = hosted_domain(portal.slug)
    portal.custom_domain = normalize_domain(portal.custom_domain)
    if portal.custom_domain:
        portal.custom_domain = validate_domain(portal.custom_domain)
        application_hosts = {
            normalize_domain(value.lstrip("."))
            for value in getattr(settings, "CUS_APP_PRIMARY_HOSTS", [])
            if value and not value.startswith(".")
        }
        if portal.custom_domain in application_hosts:
            raise ValidationError(
                {"custom_domain": "Домен внутреннего приложения использовать нельзя"}
            )
        if portal.custom_domain == portal.hosted_domain:
            raise ValidationError(
                {"custom_domain": "Свой домен должен отличаться от адреса Chatbolls"}
            )
        collision = portal.__class__.objects.exclude(pk=portal.pk).filter(
            models.Q(hosted_domain=portal.custom_domain)
            | models.Q(custom_domain=portal.custom_domain)
            | models.Q(custom_domain=portal.hosted_domain)
        )
        if collision.exists():
            raise ValidationError(
                {"custom_domain": "Этот домен уже используется другим порталом"}
            )
    elif portal.custom_domain_verified_at is not None:
        raise ValidationError(
            {"custom_domain_verified_at": "Нельзя подтвердить пустой домен"}
        )
    elif portal.__class__.objects.exclude(pk=portal.pk).filter(
        custom_domain=portal.hosted_domain
    ).exists():
        raise ValidationError({"slug": "Этот адрес уже используется другим порталом"})


def portal_public_url(*, hosted: str, custom: str = "", custom_verified: bool = False) -> str:
    host = custom if custom and custom_verified else hosted
    scheme = "https" if custom and custom_verified else settings.CUS_HELP_PUBLIC_SCHEME
    port = "" if custom and custom_verified else settings.CUS_HELP_PUBLIC_PORT
    return f"{scheme}://{host}{f':{port}' if port else ''}"


def article_public_url(article) -> str:
    """Адрес статьи в Help Center — той же формы, что читает клиент."""
    portal = article.portal
    base = portal_public_url(
        hosted=portal.hosted_domain,
        custom=portal.custom_domain,
        custom_verified=portal.custom_domain_verified_at is not None,
    )
    return f"{base}/articles/{article.slug}"
