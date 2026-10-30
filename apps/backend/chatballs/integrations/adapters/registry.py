"""Реестр адаптеров и расширений (SPEC-0037 R-3, R-5; C4 code-service-adapter-registry).

Регистрируются только доверенные модули установленной версии: список
адаптеров задаёт настройка ``CHATBALLS_SERVICE_ADAPTERS`` (пути модулей с
атрибутом ``ADAPTER``). Расширения авторизации, транспорта, преобразований и
UI-контролов имеют ключ и версию: адаптер ссылается на «ключ@версия», и новая
версия расширения не меняет поведение уже описанных адаптеров.

Каждое описание проверяется при регистрации; ошибка описания — ошибка
разработчика, и установка с таким адаптером не стартует молча.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from django.conf import settings

from chatballs.integrations.adapters.contracts import AdapterDescriptor

EXTENSION_KINDS = ("auth", "transport", "transform", "control")


class RegistryError(ValueError):
    """Описание адаптера или расширения не прошло проверку."""


@dataclass(frozen=True)
class Extension:
    kind: str
    key: str
    version: int
    implementation: Any

    @property
    def ref(self) -> str:
        return f"{self.key}@{self.version}"


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, AdapterDescriptor] = {}
        self._extensions: dict[tuple[str, str], Extension] = {}

    # Расширения ---------------------------------------------------------

    def register_extension(self, extension: Extension) -> None:
        if extension.kind not in EXTENSION_KINDS:
            raise RegistryError(f"unknown extension kind {extension.kind!r}")
        index = (extension.kind, extension.ref)
        if index in self._extensions:
            raise RegistryError(f"extension {extension.kind}:{extension.ref} is already registered")
        self._extensions[index] = extension

    def extension(self, kind: str, ref: str) -> Extension | None:
        return self._extensions.get((kind, ref))

    def has_extension(self, kind: str, ref: str) -> bool:
        return (kind, ref) in self._extensions

    def extensions(self, kind: str) -> list[Extension]:
        return [item for (item_kind, _ref), item in self._extensions.items() if item_kind == kind]

    # Адаптеры -----------------------------------------------------------

    def register_adapter(self, adapter: AdapterDescriptor) -> None:
        from chatballs.integrations.adapters.validation import validate_adapter

        if adapter.key in self._adapters:
            raise RegistryError(f"adapter {adapter.key!r} is already registered")
        problems = validate_adapter(adapter, self)
        if problems:
            raise RegistryError(f"adapter {adapter.key!r}: " + "; ".join(problems))
        self._adapters[adapter.key] = adapter

    def adapter(self, key: str) -> AdapterDescriptor | None:
        return self._adapters.get(key)

    def adapters(self) -> list[AdapterDescriptor]:
        return list(self._adapters.values())

    def catalog(self) -> list[AdapterDescriptor]:
        """Установленные адаптеры, которые администратор может подключить."""

        return [adapter for adapter in self._adapters.values() if adapter.listed]


def build_registry(adapter_modules: list[str] | tuple[str, ...], extension_modules: tuple[str, ...] = ()) -> AdapterRegistry:
    from chatballs.integrations.adapters import auth, controls, transforms, transport

    registry = AdapterRegistry()
    for module in (auth, transport, transforms, controls):
        for extension in module.builtin_extensions():
            registry.register_extension(extension)
    for path in extension_modules:
        for extension in importlib.import_module(path).EXTENSIONS:
            registry.register_extension(extension)
    for path in adapter_modules:
        module = importlib.import_module(path)
        registry.register_adapter(module.ADAPTER)
    return registry


@lru_cache(maxsize=1)
def default_registry() -> AdapterRegistry:
    return build_registry(
        tuple(getattr(settings, "CHATBALLS_SERVICE_ADAPTERS", ())),
        tuple(getattr(settings, "CHATBALLS_SERVICE_EXTENSIONS", ())),
    )


def reset_registry() -> None:
    """Для тестов: следующий вызов соберёт реестр заново по настройкам."""

    default_registry.cache_clear()
