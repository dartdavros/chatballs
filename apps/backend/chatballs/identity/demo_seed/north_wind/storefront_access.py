"""Issue generation-scoped visitor links without exposing staff credentials."""

import os
from urllib.parse import quote, urlencode

from django.core import signing

from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.north_wind.local_access import local_demo_enabled
from chatballs.identity.demo_seed.north_wind.loyalty_site import configure_loyalty_site
from chatballs.identity.demo_seed.north_wind.pickup_site import configure_pickup_site

_SALT = "north-wind-demo-storefront"
STOREFRONT_CUSTOMERS = {
    "pickup": "maria", "loyalty": "andrey", "fitting": "olga",
    "proposal": "school", "exchange": "andrey-after-purchase",
}
_VISIT_ROUTES = frozenset(STOREFRONT_CUSTOMERS.values())


def visit_path(dataset, customer="andrey", *, order_number=None, executor=False, pickup_product=None):
    if not local_demo_enabled() or not dataset.shop_state.get("storefront") or customer not in _VISIT_ROUTES:
        return None
    token = signing.dumps({
        "organization": dataset.organization_id,
        "generation": str(dataset.generation),
        "customer": customer,
        "executor": executor,
    }, salt=_SALT)
    # A fragment keeps the credential out of request targets, access logs and
    # Referer. The page forwards it to the same-origin API as a Bearer token.
    view = "executor" if executor else {"olga": "fitting", "school": "proposal", "andrey-after-purchase": "exchange"}.get(customer)
    arguments = {"view": view} if view else {}
    if view == "exchange" and order_number is not None:
        arguments["order"] = order_number
    if customer == "maria" and pickup_product:
        arguments.update(pickup_product)
    if dataset.shop_state["storefront"].get("language") == "en":
        arguments["lang"] = "en"
    query = "?" + urlencode(arguments) if arguments else ""
    return f"/chat/north-wind.html{query}#{quote(token, safe='')}"


def visit_binding(headers):
    scheme, _, token = headers.get("Authorization", "").partition(" ")
    if not local_demo_enabled() or scheme != "Bearer" or not token or len(token) > 1024:
        return None
    try:
        binding = signing.loads(token, salt=_SALT)
    except signing.BadSignature:
        return None
    return binding if binding["customer"] in _VISIT_ROUTES else None


def configure_storefront(refs):
    if not refs.recorder or not refs.recorder.dataset.shop_state.get("localTools"):
        return
    dataset = refs.recorder.dataset
    origin = os.getenv("CHATBALLS_NORTH_WIND_SITE_ORIGIN", "http://localhost")
    layout = manifest.load("north_wind", refs.language)
    _configure_widget(refs, "web", origin, layout["storefrontWidget"], "northWindStorefront")
    _configure_widget(refs, "web_help", origin, layout["supportWidget"], "northWindSupport")
    dataset.shop_state["storefront"] = {
        "widgetKey": refs.widgets["web"].public_key, "language": refs.language,
        "connectionId": refs.integrations["web"].pk, "origin": origin,
    }
    configure_pickup_site(refs)
    configure_loyalty_site(refs)
    dataset.save(update_fields=["shop_state"])


def _configure_widget(refs, key, origin, presentation, flag):
    integration, widget = refs.integrations[key], refs.widgets[key]
    integration.name = presentation["title"]
    integration.config = {
        **integration.config, **presentation, "allowed_domains": [origin], "allowed_origins": [origin],
        flag: True, "demoGeneration": str(refs.recorder.dataset.generation),
    }
    integration.save(update_fields=["name", "config"])
    widget.name = presentation["title"]
    widget.allowed_origins = [origin]
    widget.presentation_config = {**widget.presentation_config, **presentation}
    widget.save(update_fields=["name", "allowed_origins", "presentation_config", "updated_at"])
