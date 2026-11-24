"""Native invitation and live balance for the signed demo shopper."""

from django.core import signing

from chatballs.ai.tool_models import AgentTool
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.north_wind.local_access import (
    issue_local_read_token,
    local_demo_enabled,
)
from chatballs.identity.demo_seed.north_wind.local_transport import HTTP_LOYALTY_URL
from chatballs.identity.demo_seed.north_wind.orders import quote_order
from chatballs.identity.demo_seed.north_wind.seed_tools import register_local_tool
from chatballs.identity.demo_seed.north_wind.site_scenario import configure_site_scenario
from chatballs.identity.demo_seed.north_wind.state import ShopError

LOYALTY_EVENT = "north-wind.loyalty-view"
LOYALTY_TASK = "Explain the North Wind shopper's verified loyalty profile and redemption terms."
LOYALTY_TOOL = "north_wind_loyalty_profile"
_COOKIE_SALT = "north-wind-loyalty-widget"
_COOKIE_AGE = 24 * 60 * 60


def configure_loyalty_site(refs):
    dataset = refs.recorder.dataset
    agent = refs.agents["consultant"]
    copy = manifest.load("north_wind", refs.language)["loyaltySite"]
    configure_site_scenario(refs, key="loyalty",
        event=LOYALTY_EVENT, task=LOYALTY_TASK, copy=copy,
        schema=[{"name": "product", "type": "string", "maxLength": 16, "required": True}])
    integration = register_local_tool(dataset, issue_local_read_token(dataset, customer="andrey"),
        provider="HTTP", name=f"{copy['name']} · HTTP", config={
            "url": HTTP_LOYALTY_URL, "method": "POST", "read_only": True, "tool_name": LOYALTY_TOOL,
            "northWindLoyaltyRule": dataset.shop_state["loyaltySite"]["ruleId"],
            "description": "Баланс и условия списания бонусов. Read loyalty profile and redemption terms.",
            "parameters": [{"name": "product_id", "type": "string", "source": {"type": "ai"},
                            "location": "body", "required": True}],
        })
    AgentTool.objects.create(organization_id=dataset.organization_id, agent=agent, integration=integration)


def loyalty_profile(state, *, customer, product_id):
    if customer != "andrey" or customer not in state["loyaltyMembers"]:
        raise ShopError("profile_unavailable")
    quote = quote_order(state, customer=customer, product_id=product_id, size="L", bonus=0)
    language = state["storefront"]["language"]
    return {"language": language, "product": product_id, "balance": quote["bonusBalance"],
            "personalPrice": quote["personalPrice"], "allowed": product_id not in state["excludedFromBonuses"],
            "maxBonus": quote["maxBonus"]}


def add_loyalty_proof(response, request, binding, storefront):
    widget_key = storefront.get("loyaltyWidget")
    if widget_key and binding["customer"] == "andrey":
        proof = signing.dumps([binding["organization"], binding["generation"], widget_key], salt=_COOKIE_SALT)
        response.set_cookie(_cookie_name(widget_key), proof, max_age=_COOKIE_AGE, httponly=True,
                            secure=request.is_secure(), samesite="Strict", path="/api/v1/webchat/")


def allow_loyalty_session(request, widget):
    config = widget.integration.config
    if not config.get("northWindProfileWidget"):
        return True
    return bool(request.data.get("consentVersion")) and _valid_loyalty_proof(request, widget)


def allow_loyalty_event(request, widget, event_name):
    if event_name != LOYALTY_EVENT or not widget.integration.config.get("northWindStorefront"):
        return True
    return _valid_loyalty_proof(request, widget)


def can_offer_loyalty_tool(integration, conversation, launch_id):
    rule_id = integration.config.get("northWindLoyaltyRule")
    if not rule_id:
        return True
    if not (local_demo_enabled() and conversation and launch_id):
        return False
    from chatballs.webchat.proactive_models import SiteEventLaunch

    return SiteEventLaunch.objects.filter(
        pk=launch_id, organization_id=conversation.organization_id, conversation=conversation,
        rule_id=rule_id, state="running", session__connection_id=conversation.connection_id,
    ).exists()


def _valid_loyalty_proof(request, widget):
    if not local_demo_enabled():
        return False
    proof = request.COOKIES.get(_cookie_name(widget.public_key), "")
    try:
        values = signing.loads(proof, salt=_COOKIE_SALT, max_age=_COOKIE_AGE)
    except signing.BadSignature:
        return False
    return values == [widget.organization_id, widget.integration.config.get("demoGeneration"), widget.public_key]


def _cookie_name(widget_key):
    return "north-wind-profile-" + widget_key
