"""Установленные расширения участвуют в создании контекста подключения."""

import importlib
from dataclasses import replace
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from chatballs.integrations.adapters import probe_testing
from chatballs.integrations.adapters.registry import Extension, RegistryError, build_registry
from chatballs.integrations.adapters.transport import GuardedTransport
from chatballs.integrations.service_connections.binding import build_context


class InstalledExtensionTests(SimpleTestCase):
    def test_trusted_transport_is_loaded_before_the_adapter_and_used_by_its_context(self):
        transport = GuardedTransport()
        adapter = replace(probe_testing.ADAPTER, transport="vendor.secure@2")
        modules = {
            "installed.extensions": SimpleNamespace(EXTENSIONS=[Extension("transport", "vendor.secure", 2, transport)]),
            "installed.adapter": SimpleNamespace(ADAPTER=adapter),
        }
        original = importlib.import_module
        with mock.patch("chatballs.integrations.adapters.registry.importlib.import_module",
                        side_effect=lambda name: modules[name] if name in modules else original(name)):
            registry = build_registry(["installed.adapter"], ("installed.extensions",))
        context = build_context(
            tenant=None, integration=SimpleNamespace(organization_id=1, pk=None), method=adapter.auth_methods[0],
            settings={}, credentials={}, registry=registry, transport_ref=adapter.transport,
        )
        self.assertIs(context.transport, transport)
        with self.assertRaisesRegex(RegistryError, "unknown transport"):
            build_registry([]).register_adapter(adapter)
