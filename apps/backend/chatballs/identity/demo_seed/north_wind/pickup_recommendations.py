"""Project verified catalogue rows onto the demo's customer-facing cards."""

import json

from chatballs.ai.provider.demo_pickup_context import pickup_context
from chatballs.i18n import t
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS, available_choices
from chatballs.identity.demo_seed.north_wind.storefront_access import visit_path


def save_recommendations(session, message, plan, answer):
    connection = session.connection
    if not connection.config.get("northWindStorefront"):
        return
    dataset = DemoDataset.objects.filter(organization_id=session.organization_id, status=DemoDatasetStatus.INSTALLED,
                                         generation=connection.config.get("demoGeneration")).first()
    if not dataset or dataset.shop_state.get("pickupSite", {}).get("connectionId") != connection.pk:
        return
    selection = pickup_context(plan.job.messages)
    result = next((call for call in answer.tool_calls if call.name == "search_products" and not call.error), None)
    if selection is None or result is None:
        return
    criteria = selection[1]
    size = criteria["size"]
    language = dataset.shop_state["storefront"]["language"]
    rows = _cards(dataset, result.diagnostic.get("modelResult"), size, criteria["store"])
    if not rows:
        return
    message.ai_delivery["northWindRecommendations"] = {
        "size": size, "language": language, "products": rows,
        "heading": t("ai.demo_catalog_selection", language=language, size=size),
        "followup": t("ai.demo_catalog_followup", language=language),
    }
    message.save(update_fields=["ai_delivery"])


def _cards(dataset, content, size, store):
    try:
        items = json.loads(content)["products"]
        selected = available_choices(items)
    except (KeyError, TypeError, ValueError):
        return []
    cards = []
    for product in selected:
        product_id = product.get("id")
        if (product_id not in PRODUCTS or product.get("name") != PRODUCTS[product_id]["name"]
                or any(type(product.get(key)) is not int for key in ("basePrice", "insulation", "membrane"))):
            continue
        url = visit_path(dataset, "maria", pickup_product={"product": product_id, "size": size, "store": store})
        if url:
            cards.append({**{key: product[key] for key in ("id", "name", "basePrice", "insulation", "membrane")},
                          "url": url})
    return cards


def recommendation_payload(session, message):
    if not session.connection.config.get("northWindStorefront") or message.author_type != "AI":
        return {}
    recommendations = message.ai_delivery.get("northWindRecommendations")
    return {"northWindRecommendations": recommendations} if recommendations else {}
