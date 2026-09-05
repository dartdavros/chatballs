"""Оркестратор демо-сида «Северная Верфь».

Создаёт полный, взаимосвязанный набор выдуманных данных одной организации,
будто система уже работает. Запускается строго в порядке FK-зависимостей:
foundation → catalog → channels/ai → support → conversations → operations.
Идемпотентен на каждом шаге.
"""

from __future__ import annotations

from hub_platform.identity.demo_seed.loaders import (
    catalog as catalog_loader,
)
from hub_platform.identity.demo_seed.loaders import (
    channels_ai as channels_ai_loader,
)
from hub_platform.identity.demo_seed.loaders import (
    conversations as conversations_loader,
)
from hub_platform.identity.demo_seed.loaders import (
    foundation as foundation_loader,
)
from hub_platform.identity.demo_seed.loaders import (
    operations as operations_loader,
)
from hub_platform.identity.demo_seed.loaders import (
    support as support_loader,
)
from hub_platform.identity.demo_seed.refs import DemoRefs
from hub_platform.tenancy.context import TenantContext

__all__ = ["DemoRefs", "run_demo_seed"]


def run_demo_seed(
    context: TenantContext, *, refs: DemoRefs | None = None, recorder: object | None = None
) -> DemoRefs:
    """Запускает все loaders в порядке зависимостей.

    Предполагается вызов внутри ``tenant_atomic(context)``: tenant-контекст
    активирован, RLS и storage-guard работают. ``recorder`` — реестр
    установленных записей (``registry.DemoRecorder``) для точного удаления;
    loaders обращаются к нему только для записей, созданных без сигналов.
    """
    refs = refs or DemoRefs()
    refs.organization = context.organization
    refs.recorder = recorder

    foundation_loader.load(context, refs)
    catalog_loader.load(context, refs)
    channels_ai_loader.load(context, refs)
    # Поддержка раньше диалогов: диалог портала ссылается на снимок личности,
    # а статьи портала привязываются к агентам.
    support_loader.load(context, refs)
    conversations_loader.load(context, refs)
    operations_loader.load(context, refs)
    return refs
