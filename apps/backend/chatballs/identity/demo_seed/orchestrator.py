"""Оркестратор демонстрационного набора организации.

Создаёт полный, взаимосвязанный набор выдуманных данных одной организации,
будто система уже работает. Запускается строго в порядке FK-зависимостей:
foundation → channels/ai → support → conversations → operations.
Идемпотентен на каждом шаге.
"""

from __future__ import annotations

from chatballs.i18n import customer_language
from chatballs.identity.demo_seed.loaders import (
    channels_ai as channels_ai_loader,
)
from chatballs.identity.demo_seed.loaders import (
    contacts as contacts_loader,
)
from chatballs.identity.demo_seed.loaders import (
    foundation as foundation_loader,
)
from chatballs.identity.demo_seed.loaders import (
    operations as operations_loader,
)
from chatballs.identity.demo_seed.loaders import (
    support as support_loader,
)
from chatballs.identity.demo_seed.north_wind.seed_entries import load_entries
from chatballs.identity.demo_seed.north_wind.seed_executor import load_executor
from chatballs.identity.demo_seed.north_wind.seed_tools import load_local_tools
from chatballs.identity.demo_seed.north_wind.storefront_access import configure_storefront
from chatballs.identity.demo_seed.refs import DemoRefs
from chatballs.tenancy.context import TenantContext

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
    # Демо ставится на языке организации: витрина обязана совпадать с тем,
    # что человек увидит в остальном интерфейсе.
    refs.language = customer_language(context.organization)

    foundation_loader.load(context, refs)
    channels_ai_loader.load(context, refs)
    load_local_tools(refs)
    # Поддержка раньше диалогов: статьи портала привязываются к агентам.
    support_loader.load(context, refs)
    contacts_loader.load(refs)
    operations_loader.load(refs)
    configure_storefront(refs)
    load_executor(refs)
    load_entries(refs)
    return refs
