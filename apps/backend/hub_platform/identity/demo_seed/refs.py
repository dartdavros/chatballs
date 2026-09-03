"""Разделяемое состояние между loaders демо-сида.

Вынесено в отдельный модуль, чтобы избежать циклического импорта: orchestrator
импортирует loaders, а loaders импортируют ``DemoRefs``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DemoRefs:
    """Ключи → объекты моделей, создаваемые loaders.

    Каждый loader вешает на ``refs`` созданные объекты, чтобы последующие
    шаги ссылались на них по строковым ключам из манифестов (не по PK).
    """

    organization: object | None = None
    subscription: object | None = None
    departments: dict[str, object] = field(default_factory=dict)
    memberships: dict[str, object] = field(default_factory=dict)
    users: dict[str, object] = field(default_factory=dict)
    products: dict[str, object] = field(default_factory=dict)
    integrations: dict[str, object] = field(default_factory=dict)
    channels: dict[str, object] = field(default_factory=dict)
    knowledge: dict[str, object] = field(default_factory=dict)
    contacts: dict[str, object] = field(default_factory=dict)
    identities: dict[str, object] = field(default_factory=dict)
    conversations: dict[str, object] = field(default_factory=dict)
    support_contracts: dict[str, object] = field(default_factory=dict)
    identity_snapshots: dict[str, object] = field(default_factory=dict)
