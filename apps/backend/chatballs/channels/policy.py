"""Политика канала и её инварианты (SPEC-HUB-0027 §3.2, ADR-HUB-0037 §7).

Источник истины — булевы поля `Channel`. Продуктовой идентичности больше нет
(ADR-HUB-0045: сущность `Product` удалена), поэтому коммерческие действия и
attribution запрещены безусловно. Проверяются по итоговому состоянию, а не по
переданным полям, — частичное применение запрещено.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from django.core.exceptions import ValidationError

from chatballs.channels.models import Channel

POLICY_FIELDS = (
    "allow_anonymous_sessions",
    "allow_self_reported_contact",
    "allow_sales_attribution",
    "allow_checkout_actions",
)

# Ключ payload -> имя поля модели (SPEC §6.1).
POLICY_API_FIELDS = {
    "allowAnonymousSessions": "allow_anonymous_sessions",
    "allowSelfReportedContact": "allow_self_reported_contact",
    "allowSalesAttribution": "allow_sales_attribution",
    "allowCheckoutActions": "allow_checkout_actions",
}


@dataclass(frozen=True, slots=True)
class ChannelPolicy:
    allow_anonymous_sessions: bool
    allow_self_reported_contact: bool
    allow_sales_attribution: bool
    allow_checkout_actions: bool

    @classmethod
    def from_channel(cls, channel: Channel) -> ChannelPolicy:
        return cls(**{name: getattr(channel, name) for name in POLICY_FIELDS})

    def replace_fields(self, changes: dict[str, bool]) -> ChannelPolicy:
        return replace(self, **changes)

    def as_model_fields(self) -> dict[str, bool]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    def as_payload(self) -> dict[str, bool]:
        return {key: getattr(self, name) for key, name in POLICY_API_FIELDS.items()}


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    rule: str
    field: str
    detail: str

    def payload(self) -> dict[str, str]:
        return {"rule": self.rule, "field": self.field, "detail": self.detail}


def policy_violations(*, policy: ChannelPolicy) -> tuple[PolicyViolation, ...]:
    """Нарушения P1-P2 для итогового состояния канала (SPEC §3.2)."""
    violations: list[PolicyViolation] = []
    if policy.allow_checkout_actions:
        violations.append(
            PolicyViolation(
                "P1",
                "allowCheckoutActions",
                "Коммерческие действия недоступны",
            )
        )
    if policy.allow_sales_attribution:
        violations.append(
            PolicyViolation(
                "P2",
                "allowSalesAttribution",
                "Attribution недоступна",
            )
        )
    return tuple(violations)


def require_valid_policy(*, policy: ChannelPolicy) -> None:
    violations = policy_violations(policy=policy)
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
