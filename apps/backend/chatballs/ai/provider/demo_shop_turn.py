"""Deterministic offline order turn using the real tool and skill operations."""

import json
import re

from chatballs.ai.provider.base import ToolCall
from chatballs.ai.provider.demo import HANDOFF_TOKEN
from chatballs.ai.skill_templates.order_basis import CARD_ID, STATUS_ID
from chatballs.ai.turn_skills import LOAD_SKILL
from chatballs.ai.turn_templates import PREPARE_REPLY
from chatballs.i18n import t

MCP_ORDER = "get_order_status"
HTTP_STATUS = "north_wind_delivery_status"
_STATUSES = {
    "reserved": ("Зарезервирован", "Reserved"),
    "ready": ("Готов к выдаче", "Ready for pickup"),
    "collected": ("Получен", "Collected"),
    "delayed": ("Задерживается", "Delayed"),
}


def plan_order_turn(messages, tools):
    available = {item.name for item in tools}
    if not {MCP_ORDER, HTTP_STATUS}.issubset(available):
        return None
    user_index = next((index for index in reversed(range(len(messages)))
                       if messages[index].role == "user"), None)
    if user_index is None:
        return None
    question = messages[user_index].content
    order_number = re.search(r"\b\d{4,10}\b", question)
    if order_number is None or not re.search(r"заказ|статус|order|status", question, re.I):
        return None

    skill_load = next((name for name in available if name.startswith(LOAD_SKILL)), None)
    prepare_reply = next((name for name in available if name.startswith(PREPARE_REPLY)), None)
    skill_id = _order_skill(messages[:user_index])
    language = "ru" if re.search("[а-я]", question, re.I) else "en"
    unavailable = f'{t("ai.demo_handover", language=language)}\n{HANDOFF_TOKEN}'
    if not skill_id or not skill_load:
        return unavailable, ()
    results = _turn_results(messages[user_index + 1:])
    if prepare_reply and prepare_reply in results:
        return results[prepare_reply].get("final_response", unavailable), ()
    if skill_load not in results:
        return "", (_call(skill_load, {"skill_id": skill_id}),)
    if "templates" not in results[skill_load]:
        return unavailable, ()
    if MCP_ORDER not in results:
        arguments = {"order_number": int(order_number.group())}
        return "", (_call(MCP_ORDER, arguments), _call(HTTP_STATUS, arguments))

    details = results[MCP_ORDER]
    shipment = results.get(HTTP_STATUS) or {}
    if not prepare_reply or details.get("number") != shipment.get("number") or not details.get("name"):
        return unavailable, ()
    data = _prepare_arguments(details, shipment, question, language)
    if data is None:
        return unavailable, ()
    template_id = _matching_template(results[skill_load]["templates"], data["template_id"])
    if template_id is None:
        return unavailable, ()
    data["template_id"] = template_id
    return "", (_call(prepare_reply, {"skill_id": skill_id, **data}),)


def _matching_template(templates, basis_id):
    required = {"order_no", "items", "total"} if basis_id == CARD_ID else {"order_no", "status"}
    for template in templates:
        properties = template.get("schema", {}).get("properties", {})
        if template.get("id") == basis_id or required.issubset(properties):
            return template.get("id")
    return None


def _order_skill(messages):
    for message in reversed(messages):
        if message.role != "system" or LOAD_SKILL not in message.content:
            continue
        items = _decode(message.content.rsplit("\n", 1)[-1], [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("name") in {
                    t("skills.orders_name", language="ru"), t("skills.orders_name", language="en"),
                }:
                    return item.get("id")
    return None


def _turn_results(messages):
    ids, results = {}, {}
    for message in messages:
        ids.update({call.id: call.name for call in message.tool_calls})
        if message.role == "tool" and message.tool_call_id in ids:
            value = _decode(message.content, {})
            results[ids[message.tool_call_id]] = value if isinstance(value, dict) else {}
    return results


def _decode(text, default):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


def _prepare_arguments(details, shipment, question, language):
    number = str(details["number"])
    if re.search(r"статус|status|доставк|где", question, re.I):
        status = _STATUSES.get(shipment.get("status"))
        if status is None:
            return None
        data = {"order_no": number, "status": status[language == "en"]}
        if shipment.get("eta"):
            data["eta"] = shipment["eta"]
        return {"template_id": STATUS_ID, "data": data}
    total = details.get("total")
    if type(total) is not int:
        return None
    return {"template_id": CARD_ID, "data": {
        "order_no": number, "total": total,
        "items": [{"title": details["name"], "qty": 1, "price": total, "sum": total}],
    }}


def _call(name, arguments):
    return ToolCall(id=f"north-wind-{name}", name=name, arguments=arguments)
