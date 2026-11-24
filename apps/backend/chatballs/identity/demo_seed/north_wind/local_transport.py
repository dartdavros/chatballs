"""Local destinations reserved for signed North Wind tool requests."""

import ipaddress

from chatballs.i18n import t
from chatballs.identity.demo_seed.north_wind.local_access import read_local_binding
from chatballs.integrations.outbound import resolve_host
from chatballs.integrations.tool_network import PRIVATE_NETWORKS, ToolAddressRejected, ToolTarget

MCP_URL = "http://north-wind-mcp:8000/mcp"
HTTP_ROOT = "http://backend-app:8000/api/v1/demo-local/shop"
HTTP_ORDER_URL = f"{HTTP_ROOT}/shipment-status/"
HTTP_LOYALTY_URL = f"{HTTP_ROOT}/loyalty-profile/"
HTTP_DELIVERY_CHECK_URL = f"{HTTP_ROOT}/delivery-check/"
HTTP_DELIVERY_RESULT_URL = f"{HTTP_ROOT}/delivery-result/"
HTTP_DELIVERY_HEALTH_URL = f"{HTTP_ROOT}/delivery-health/"

_ROUTES = {
    MCP_URL: ("north-wind-mcp", "/mcp"),
    HTTP_ORDER_URL: ("backend-app", "/api/v1/demo-local/shop/shipment-status/"),
    HTTP_LOYALTY_URL: ("backend-app", "/api/v1/demo-local/shop/loyalty-profile/"),
    HTTP_DELIVERY_CHECK_URL: ("backend-app", "/api/v1/demo-local/shop/delivery-check/"),
    HTTP_DELIVERY_RESULT_URL: ("backend-app", "/api/v1/demo-local/shop/delivery-result/"),
    HTTP_DELIVERY_HEALTH_URL: ("backend-app", "/api/v1/demo-local/shop/delivery-health/"),
}


def local_demo_target(url, headers):
    route = _ROUTES.get(url)
    binding = read_local_binding(headers) if route else None
    carrier_only = {HTTP_DELIVERY_CHECK_URL, HTTP_DELIVERY_RESULT_URL, HTTP_DELIVERY_HEALTH_URL}
    if (not binding or (url in carrier_only and binding["customer"] != "pavel")
            or (url == HTTP_LOYALTY_URL and binding["customer"] != "andrey")):
        return None
    host, path = route
    addresses = resolve_host(host, 8000)
    if not addresses or any(
        not any(ipaddress.ip_address(address) in network for network in PRIVATE_NETWORKS)
        for address in addresses
    ):
        raise ToolAddressRejected("internal", t("integrations.tool_address_local"))
    return ToolTarget("http", host, 8000, addresses[0], path)
