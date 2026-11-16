"""One closed-schema runtime boundary using the accepted local OpenAPI modules."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml

from chatballs.ai.external_agents.canonical import decode

CONTRACT_ROOT = Path(__file__).resolve().parents[5] / "packages/contracts/external-agent-v1"


def _integer(checker, value):
    from jsonschema import Draft202012Validator

    if isinstance(value, Decimal):
        return value.is_finite() and value == value.to_integral_value()
    return Draft202012Validator.TYPE_CHECKER.is_type(value, "integer")


@lru_cache(maxsize=1)
def _validator_type():
    # Optional execution stays cheap for builtin-only installations. Dependencies
    # are installed in the backend image, and loaded only at this protocol boundary.
    from jsonschema import Draft202012Validator, validators

    return validators.extend(Draft202012Validator, type_checker=
                             Draft202012Validator.TYPE_CHECKER.redefine("integer", _integer))


@lru_cache(maxsize=1)
def _modules():
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    documents = {path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
                 for path in CONTRACT_ROOT.glob("*.yaml")}
    if "catalogs.yaml" not in documents:
        raise RuntimeError("external_agent_contract_missing")
    registry = Registry()
    for name, document in documents.items():
        registry = registry.with_resource(
            f"https://contracts.chatballs.local/{name}",
            Resource.from_contents(document, default_specification=DRAFT202012),
        )
    return registry


def validate(module: str, schema: str, value):
    from jsonschema import FormatChecker

    validator = _validator_type()(
        {"$ref": f"https://contracts.chatballs.local/{module}#/{schema}"},
        registry=_modules(), format_checker=FormatChecker(),
    )
    if not validator.is_valid(value):
        raise ValueError("invalid_request")
    return value


def parse(module: str, schema: str, body: bytes):
    return validate(module, schema, decode(body))


def capabilities(body: bytes):
    value = parse("catalogs.yaml", "Capabilities", body)
    directions = value["directions"]
    if set(value["contentTypes"]) != set(directions["fromChatballs"]) | set(directions["toChatballs"]):
        raise ValueError("invalid_request")
    # These two protocol metadata properties are validated integral values.
    # Preserve JSON-number equivalence (e.g. 262144.0) in the stored snapshot.
    for key in ("dedupRetentionSeconds", "maxJsonBytes"):
        value[key] = int(value[key])
    return value


def error_payload(code: str, trace_id: str, *, retryable=False):
    return validate("common.yaml", "Error", {
        "version": "1", "error": {"code": code, "traceId": trace_id, "retryable": retryable},
    })
