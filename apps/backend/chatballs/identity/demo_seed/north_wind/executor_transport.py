"""An isolated TLS route reserved for the signed demo executor requests."""

import ipaddress
import re
from urllib.parse import urlsplit

from chatballs.identity.demo_seed.north_wind.executor_scope import EXECUTOR_CA, EXECUTOR_ORIGIN, read_executor_key
from chatballs.integrations.adapters.transport import GuardedTransport, TransportError
from chatballs.integrations.outbound import resolve_host
from chatballs.integrations.tool_network import PRIVATE_NETWORKS, ToolTarget

_ORIGIN = urlsplit(EXECUTOR_ORIGIN)
_REQUEST_PATH = re.compile(r"/executor/requests/[0-9a-f-]{36}(/cancel)?\Z")


def _allowed(method, path):
    if path in {"/executor/capabilities", "/executor/requests", "/executor/reset"}:
        return method == ("GET" if path.endswith("/capabilities") else "POST")
    match = _REQUEST_PATH.fullmatch(path)
    return bool(match and method == ("POST" if match.group(1) else "GET"))


def send_external(request, *, limits):
    url = urlsplit(request.url)
    transport = GuardedTransport()
    if url.hostname != _ORIGIN.hostname:
        return transport.send(request, limits=limits)
    if ((url.scheme, url.netloc) != (_ORIGIN.scheme, _ORIGIN.netloc) or url.query or url.fragment
            or not _allowed(request.method, url.path) or not read_executor_key(request.headers.get("Authorization"))):
        raise TransportError("address_forbidden")
    addresses = resolve_host(_ORIGIN.hostname, _ORIGIN.port)
    if not addresses or any(
        not any(ipaddress.ip_address(address) in network for network in PRIVATE_NETWORKS) for address in addresses
    ):
        raise TransportError("address_forbidden")
    target = ToolTarget("https", _ORIGIN.hostname, _ORIGIN.port, addresses[0], url.path)
    return transport.send_pinned(request, limits=limits, target=target, ca_file=EXECUTOR_CA)
