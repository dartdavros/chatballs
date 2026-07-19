"""Политика канала и её инварианты (SPEC-HUB-0027 §3.2, ADR-HUB-0037 §7).

Источник истины — пять булевых полей `Channel`. Пресет существует только в API
и UI: он заполняет флаги при создании и полем модели не является.

Инварианты выражают одно правило `ADR-HUB-0019`: непродуктовый канал не
формирует коммерческих действий. Проверяются по итоговому состоянию, а не по
переданным полям, — частичное применение запрещено.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from django.core.exceptions import ValidationError

from hub_platform.channels.models import Channel

POLICY_FIELDS = (
    "requires_authenticated_product_identity",
    "allow_anonymous_sessions",
    "allow_self_reported_contact",
    "allow_sales_attribution",
    "allow_checkout_actions",
)

# Ключ payload -> имя поля модели (SPEC §6.1).
POLICY_API_FIELDS = {
    "requiresAuthenticatedProductIdentity": "requires_authenticated_product_identity",
    "allowAnonymousSessions": "allow_anonymous_sessions",
    "allowSelfReportedContact": "allow_self_reported_contact",
    "allowSalesAttribution": "allow_sales_attribution",
    "allowCheckoutActions": "allow_checkout_actions",
}


class PolicyPreset:
    SALES = "SALES"
    SUPPORT = "SUPPORT"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True, slots=True)
class ChannelPolicy:
    requires_authenticated_product_identity: bool
    allow_anonymous_sessions: bool
    allow_self_reported_contact: bool
    allow_sales_attribution: bool
    allow_checkout_actions: bool

    @classmethod
    def from_channel(cls, channel: Channel) -> ChannelPolicy:
        return cls(**{name: getattr(channel, name) for name in POLICY_FIELDS})

    @classmethod
    def from_preset(cls, preset: str) -> ChannelPolicy:
        return _PRESETS[preset]

    def replace_fields(self, changes: dict[str, bool]) -> ChannelPolicy:
        return replace(self, **changes)

    def as_model_fields(self) -> dict[str, bool]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    def as_payload(self) -> dict[str, bool]:
        return {key: getattr(self, name) for key, name in POLICY_API_FIELDS.items()}


# SPEC §3.3. SALES и SUPPORT требуют продукта — иначе нарушают P1-P3.
_PRESETS = {
    PolicyPreset.SALES: ChannelPolicy(
        requires_authenticated_product_identity=False,
        allow_anonymous_sessions=True,
        allow_self_reported_contact=True,
        allow_sales_attribution=True,
        allow_checkout_actions=True,
    ),
    # Комбинация support-канала из SPEC-HUB-0010 §4.2.
    PolicyPreset.SUPPORT: ChannelPolicy(
        requires_authenticated_product_identity=True,
        allow_anonymous_sessions=False,
        allow_self_reported_contact=False,
        allow_sales_attribution=False,
        allow_checkout_actions=False,
    ),
}


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    rule: str
    field: str
    detail: str

    def payload(self) -> dict[str, str]:
        return {"rule": self.rule, "field": self.field, "detail": self.detail}


def policy_violations(
    *, policy: ChannelPolicy, has_product: bool
) -> tuple[PolicyViolation, ...]:
    """Нарушения P1-P5 для итогового состояния канала (SPEC §3.2)."""
    violations: list[PolicyViolation] = []
    if not has_product:
        if policy.allow_checkout_actions:
            violations.append(
                PolicyViolation(
                    "P1",
                    "allowCheckoutActions",
                    "Коммерческие действия недоступны непродуктовому каналу",
                )
            )
        if policy.allow_sales_attribution:
            violations.append(
                PolicyViolation(
                    "P2",
                    "allowSalesAttribution",
                    "Attribution недоступна непродуктовому каналу",
                )
            )
        if policy.requires_authenticated_product_identity:
            violations.append(
                PolicyViolation(
                    "P3",
                    "requiresAuthenticatedProductIdentity",
                    "Продуктовая идентичность требует продукта",
                )
            )
    if policy.requires_authenticated_product_identity:
        if policy.allow_anonymous_sessions:
            violations.append(
                PolicyViolation(
                    "P4",
                    "allowAnonymousSessions",
                    "Анонимные сессии несовместимы с обязательной идентичностью",
                )
            )
        if policy.allow_self_reported_contact:
            violations.append(
                PolicyViolation(
                    "P5",
                    "allowSelfReportedContact",
                    "Самозаявленный контакт несовместим с обязательной идентичностью",
                )
            )
    return tuple(violations)


def require_valid_policy(*, policy: ChannelPolicy, has_product: bool) -> None:
    violations = policy_violations(policy=policy, has_product=has_product)
    if violations:
        raise PolicyInvariantError(violations)


class PolicyInvariantError(ValidationError):
    """Отклонение целиком: канал не сохраняется ни в каком виде."""

    def __init__(self, violations: tuple[PolicyViolation, ...]) -> None:
        self.violations = violations
        super().__init__("; ".join(violation.detail for violation in violations))

    def payload(self) -> dict[str, object]:
        return {
            "detail": "; ".join(violation.detail for violation in self.violations),
            "violations": [violation.payload() for violation in self.violations],
        }
