"""Политика канала: что разрешено в точке входа.

Инвариантов у политики больше нет. P3-P5 (продуктовая идентичность) сняты
вместе с сущностью `Product` (ADR-CHATBALLS-0045), P1-P2 — вместе с полями
`allow_checkout_actions` и `allow_sales_attribution`: домена продаж нет с
ADR-CHATBALLS-0041, и запрещать в них было уже нечего. Поэтому здесь остались
только состав полей и их отображение в payload; проверка целевого состояния
удалена вместе с последним правилом.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from chatballs.channels.models import Channel

POLICY_FIELDS = (
    "allow_anonymous_sessions",
    "allow_self_reported_contact",
)

# Ключ payload -> имя поля модели.
POLICY_API_FIELDS = {
    "allowAnonymousSessions": "allow_anonymous_sessions",
    "allowSelfReportedContact": "allow_self_reported_contact",
}


@dataclass(frozen=True, slots=True)
class ChannelPolicy:
    allow_anonymous_sessions: bool
    allow_self_reported_contact: bool

    @classmethod
    def from_channel(cls, channel: Channel) -> ChannelPolicy:
        return cls(**{name: getattr(channel, name) for name in POLICY_FIELDS})

    def as_model_fields(self) -> dict[str, bool]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

    def as_payload(self) -> dict[str, bool]:
        return {key: getattr(self, name) for key, name in POLICY_API_FIELDS.items()}
