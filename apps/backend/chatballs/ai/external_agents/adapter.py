"""Internal protocol profile: registered service adapter with no scenario operations."""

from urllib.parse import urlsplit

from chatballs.integrations.adapters.auth import BearerAuth, OutboundRequest
from chatballs.integrations.adapters.contracts import (
    AdapterDescriptor,
    AuthMethod,
    Limits,
    Presentation,
)
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.adapters.transport import GuardedTransport, TransportError
from chatballs.integrations.outbound import OutboundUrlRejected, clean_config_url

PROFILE = "external_agent_v1"
ADAPTER = AdapterDescriptor(
    key=PROFILE, contract_version=1, listed=False, operations=(),
    presentation=Presentation("external.title", "external.title", "external.title", "", "", "external.address"),
    settings=TypeSpec("object", properties=(("base_url", TypeSpec("string", required=True)),)),
    auth_methods=(AuthMethod("bearer", "bearer@1", "external.key", TypeSpec("object", properties=(
        ("token", TypeSpec("string", required=True, secret=True)),
    ))),),
)


def clean_address(value):
    address = clean_config_url(value, schemes=frozenset({"https"})).rstrip("/")
    parsed = urlsplit(address)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("invalid_request")
    return address


def check_capabilities(address, credential):
    from chatballs.ai.external_agents.contracts import capabilities

    request = OutboundRequest("GET", clean_address(address) + "/capabilities",
                              headers={"Accept": "application/json"})
    request = BearerAuth().prepare(request, {"token": credential}, {})
    try:
        response = GuardedTransport().send(request, limits=Limits(
            timeout_seconds=10, max_response_bytes=262144, max_file_bytes=262144,
        ))
    except (OutboundUrlRejected, OSError) as error:
        raise TransportError("capabilities_unavailable") from error
    if response.status in {401, 403}:
        raise TransportError("capabilities_access_denied")
    if response.status >= 500:
        raise TransportError("capabilities_unavailable")
    if response.status != 200 or response.content_type != "application/json" or response.file:
        raise TransportError("incompatible_capabilities")
    try:
        return capabilities(response.body)
    except (ValueError, UnicodeError) as error:
        raise TransportError("incompatible_capabilities") from error
