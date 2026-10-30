"""Схемы и реестр адаптеров (SPEC-0037 R-3, R-4, R-30)."""

from __future__ import annotations

from dataclasses import replace

from django.test import SimpleTestCase

from chatballs.integrations.adapters import probe_testing
from chatballs.integrations.adapters.contracts import (
    Delivery,
    Effect,
    EventDescriptor,
    Mode,
    OperationDescriptor,
    OperationHandlers,
    RetryStrategy,
    TemplateStep,
)
from chatballs.integrations.adapters.registry import RegistryError, build_registry
from chatballs.integrations.adapters.schema import (
    SchemaDefinitionError,
    TypeSpec,
    validate_spec,
    validate_value,
)

BITRIX = "chatballs.integrations.adapters.bitrix24"
PROBE = "chatballs.integrations.adapters.probe_testing"
FILE_ID = "8b1f3a52-9c0e-4f5b-8d1e-2f7a6c9e0b11"


def _codes(spec: TypeSpec, value) -> set[tuple[str, str]]:
    return {(issue.path, issue.code) for issue in validate_value(spec, value)}


class SchemaTests(SimpleTestCase):
    def test_nested_lists_dates_lookups_and_files_are_accepted(self) -> None:
        order = {
            "number": "A-1",
            "placed_on": "2026-10-23",
            "status": "paid",
            "manager": None,
            "lines": [{"sku": "x", "qty": 2}],
            "invoice": {"fileId": FILE_ID},
        }

        self.assertEqual(validate_value(probe_testing.ORDER, order), [])

    def test_every_problem_is_reported_with_its_path(self) -> None:
        order = {
            "placed_on": "23.10.2026",
            "status": "lost",
            "lines": [{"qty": "two"}],
            "invoice": {"fileId": "not-a-uuid"},
            "extra": 1,
        }

        self.assertEqual(
            _codes(probe_testing.ORDER, order),
            {
                ("number", "required"),
                ("placed_on", "type"),
                ("status", "choice"),
                ("lines[0].sku", "required"),
                ("lines[0].qty", "type"),
                ("invoice", "type"),
                ("extra", "unknown"),
            },
        )

    def test_null_is_allowed_only_where_nullable(self) -> None:
        spec = TypeSpec("object", properties=(("a", TypeSpec("string", nullable=True)), ("b", TypeSpec("integer"))))

        self.assertEqual(_codes(spec, {"a": None, "b": None}), {("b", "null")})

    def test_required_value_is_not_filled_by_a_blank_string(self) -> None:
        spec = TypeSpec("object", properties=(("title", TypeSpec("string", required=True)),))

        self.assertEqual(_codes(spec, {"title": "  "}), {("title", "required")})

    def test_open_object_keeps_fields_it_does_not_describe(self) -> None:
        self.assertEqual(validate_value(TypeSpec("object", open=True), {"ANY_FIELD": 1}), [])

    def test_broken_schema_is_rejected(self) -> None:
        for spec in (TypeSpec("decimal"), TypeSpec("array"), TypeSpec("enum"), TypeSpec("lookup"), TypeSpec("string", pattern="(")):
            with self.subTest(spec=spec.type), self.assertRaises(SchemaDefinitionError):
                validate_spec(spec)

    def test_mcp_numeric_enum_keeps_its_json_type_and_nullable(self) -> None:
        from chatballs.integrations.adapters.json_schema import typespec_from_json_schema

        spec = typespec_from_json_schema({"type": ["integer", "null"], "enum": [1, 2, None]})
        self.assertEqual([option.value for option in spec.options], [1, 2])
        self.assertEqual(validate_value(spec, 2), [])
        self.assertEqual(validate_value(spec, None), [])
        self.assertEqual(_codes(spec, "2"), {("$", "choice")})
        self.assertEqual(_codes(spec, True), {("$", "choice")})


def _execute(*args):
    raise AssertionError("not called in registry tests")


class RegistryTests(SimpleTestCase):
    def test_installed_adapters_register_without_core_changes(self) -> None:
        registry = build_registry([BITRIX, PROBE])

        self.assertEqual({adapter.key for adapter in registry.catalog()}, {"bitrix24", "probe"})
        probe = registry.adapter("probe")
        self.assertEqual(probe.operation("export.run").mode, Mode.LONG)
        self.assertEqual({event.delivery for event in probe.events}, {Delivery.WEBHOOK, Delivery.POLL})
        self.assertTrue(registry.has_extension("auth", "oauth2@1"))
        self.assertTrue(registry.has_extension("transform", "list.of_object@1"))

    def test_catalog_lists_only_what_is_installed(self) -> None:
        self.assertEqual([adapter.key for adapter in build_registry([BITRIX]).catalog()], ["bitrix24"])
        self.assertEqual(build_registry([]).catalog(), [])

    def _register(self, adapter) -> str:
        registry = build_registry([])
        with self.assertRaises(RegistryError) as raised:
            registry.register_adapter(adapter)
        return str(raised.exception)

    def _operation(self, **changes) -> OperationDescriptor:
        base = OperationDescriptor(
            key="op", title_key="", effect=Effect.CREATE, input=TypeSpec("object"), output=TypeSpec("object"),
            handlers=OperationHandlers(execute=_execute),
        )
        return replace(base, **changes)

    def test_declared_capabilities_need_their_handlers(self) -> None:
        cases = {
            "long operation needs resume handler": self._operation(mode=Mode.LONG),
            "reconcile strategy needs reconcile handler": self._operation(retry=RetryStrategy.RECONCILE),
            "cancellable operation needs cancel handler": self._operation(cancellable=True),
            "execute handler is missing": self._operation(handlers=OperationHandlers()),
            "safe_read strategy is only for read operations": self._operation(retry=RetryStrategy.SAFE_READ),
        }
        for message, operation in cases.items():
            with self.subTest(message):
                adapter = replace(probe_testing.ADAPTER, operations=probe_testing.OPERATIONS + (operation,))
                self.assertIn(message, self._register(adapter))

    def test_events_need_ingress_or_poll_handlers(self) -> None:
        webhook = EventDescriptor(key="paid", title_key="", payload=TypeSpec("object"), delivery=Delivery.WEBHOOK)
        poll = EventDescriptor(key="changed", title_key="", payload=TypeSpec("object"), delivery=Delivery.POLL)

        message = self._register(replace(probe_testing.ADAPTER, events=(webhook, poll)))

        self.assertIn("event paid: ingress handler is missing", message)
        self.assertIn("event changed: poll handler is missing", message)

    def test_access_check_must_only_read(self) -> None:
        method = replace(probe_testing.API_KEY, check=replace(probe_testing.API_KEY.check, operation="order.create"))

        message = self._register(replace(probe_testing.ADAPTER, auth_methods=(method,)))

        self.assertIn("check must use a read operation", message)

    def test_unknown_extensions_and_template_targets_are_rejected(self) -> None:
        method = replace(probe_testing.API_KEY, extension="magic@9")
        template = replace(
            probe_testing.ADAPTER.templates[0],
            steps=(TemplateStep(id="x", title_key="", target="service:missing", inputs={"a": {"transform": "nope@1"}}),),
        )

        message = self._register(replace(probe_testing.ADAPTER, auth_methods=(method,), templates=(template,)))

        self.assertIn("unknown auth extension magic@9", message)
        self.assertIn("unknown operation missing", message)
        self.assertIn("unknown transform nope@1", message)

    def test_adapter_key_is_unique(self) -> None:
        registry = build_registry([PROBE])
        with self.assertRaises(RegistryError):
            registry.register_adapter(probe_testing.ADAPTER)

    def test_settings_controls_must_be_installed_and_match_the_schema(self) -> None:
        for control, expected in (("custom@7", "unknown control custom@7"), ("toggle@1", "does not support string")):
            with self.subTest(control=control):
                settings = TypeSpec("object", properties=(("region", TypeSpec("string", control=control)),))
                self.assertIn(expected, self._register(replace(probe_testing.ADAPTER, settings=settings)))

    def test_form_api_preserves_control_version(self) -> None:
        from chatballs.integrations.service_connections.payloads import field_payload

        self.assertEqual(field_payload("region", TypeSpec("string", control="custom@7"))["control"], "custom@7")
