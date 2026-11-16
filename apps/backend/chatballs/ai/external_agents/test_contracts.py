import copy
import json
from decimal import Decimal

import yaml
from django.test import SimpleTestCase

from chatballs.ai.external_agents import canonical, contracts
from chatballs.ai.external_agents.adapter import check_capabilities
from chatballs.ai.external_agents.testing import CAPABILITIES
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.transport import (
    GuardedTransport,
    TransportError,
    TransportResponse,
)


class ContractTests(SimpleTestCase):
    def test_accepted_canonical_vectors_and_exact_large_numbers(self):
        vectors = yaml.safe_load((contracts.CONTRACT_ROOT / "canonicalization.yaml").read_text(encoding="utf-8"))["vectors"]
        for vector in vectors:
            with self.subTest(vector["name"]):
                left = canonical.canonical_bytes(canonical.decode(vector["left"].encode()))
                right = canonical.canonical_bytes(canonical.decode(vector["right"].encode()))
                self.assertEqual(left == right, vector["equal"])
                self.assertEqual(left.decode(), vector["canonical"])
        self.assertNotEqual(canonical.canonical_bytes(Decimal("1.00000000000000000000000000001")),
                            canonical.canonical_bytes(1))
        for raw in [b'NaN', b'{"n":1,"n":2}', b'"\\ud800"']:
            with self.assertRaises((ValueError, UnicodeError)):
                canonical.canonical_bytes(canonical.decode(raw))
        with self.assertRaises(ValueError):
            canonical.canonical_bytes(1.0)

    def test_contract_examples_use_same_runtime_validator(self):
        examples = yaml.safe_load((contracts.CONTRACT_ROOT / "examples.yaml").read_text(encoding="utf-8"))
        prepared = []
        for valid in (True, False):
            for example in examples["valid" if valid else "invalid"]:
                if "fromValid" in example:
                    original = prepared[example["fromValid"]]
                    reference, value = original[0], copy.deepcopy(original[1])
                    for path, replacement in example.get("set", {}).items():
                        target = value
                        keys = path.split(".")
                        for key in keys[:-1]:
                            target = target[key]
                        target[keys[-1]] = replacement
                    for path in example.get("remove", []):
                        target = value
                        keys = path.split(".")
                        for key in keys[:-1]:
                            target = target[key]
                        del target[keys[-1]]
                else:
                    reference, value = example["schema"], example["value"]
                module, schema = reference.split("#/")
                with self.subTest(example["name"]):
                    if valid:
                        contracts.validate(module, schema, value)
                        prepared.append((reference, value))
                    else:
                        with self.assertRaises(ValueError):
                            contracts.validate(module, schema, value)

    def test_incompatible_capabilities_and_read_only_transport_boundary(self):
        from unittest.mock import patch

        valid = copy.deepcopy(CAPABILITIES)
        invalid = []
        for field in ["directions", "versions", "callbacks", "cancel", "dedupRetentionSeconds"]:
            candidate = copy.deepcopy(valid)
            del candidate[field]
            invalid.append(candidate)
        for value in ["2", None]:
            invalid.append({**valid, "versions": [value]})
        invalid.extend([{**valid, "durableIdempotency": False}, {**valid, "extra": True},
                        {**valid, "directions": {**valid["directions"], "toChatballs": ["text"]}}])
        for value in [valid, *invalid]:
            with self.subTest(value=value), patch.object(GuardedTransport, "send", return_value=TransportResponse(
                200, "application/json", "", body=json.dumps(value).encode(),
            )) as send:
                if value == valid:
                    self.assertEqual(check_capabilities("https://executor.example.invalid/v1", "secret"), value)
                else:
                    with self.assertRaises(TransportError):
                        check_capabilities("https://executor.example.invalid/v1", "secret")
                self.assertEqual(send.call_args.args[0].method, "GET")
        self.assertEqual(default_registry().adapter("external_agent_v1").operations, ())

    def test_digest_is_scoped_and_independent_of_bearer(self):
        arguments = {"operation": "results", "route": ["connection", "conversation"], "body": {"n": 9007199254740993}}
        digest = canonical.digest("deduplication-key", **arguments)
        self.assertEqual(digest, canonical.digest("deduplication-key", **arguments))
        self.assertNotEqual(digest, canonical.digest("different-key", **arguments))
        self.assertNotEqual(digest, canonical.digest("deduplication-key", **{**arguments, "route": ["other"]}))

    def test_formats_and_integral_decimal_tokens_are_validated(self):
        for value in ("not-a-dateZ", "2026-02-31T12:00:00Z", "2026-11-15T99:00:00Z"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                contracts.validate("common.yaml", "UTC", value)
        candidate = json.dumps(CAPABILITIES).replace("2592000", "2592000.0").encode()
        self.assertEqual(contracts.capabilities(candidate)["dedupRetentionSeconds"], Decimal("2592000.0"))
