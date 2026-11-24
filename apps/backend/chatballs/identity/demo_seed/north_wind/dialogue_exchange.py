"""Order status, size exchange and the separate refund in the prepared thread."""

import re

from chatballs.identity.demo_seed.north_wind.after_sales import exchange_options
from chatballs.identity.demo_seed.north_wind.delivery import shipment_status
from chatballs.identity.demo_seed.north_wind.dialogue_input import (
    Reply,
    confirmation,
    localized,
    pickup_in,
)
from chatballs.identity.demo_seed.north_wind.orders import find_order

_STATUS = {"ready": ("Готов к выдаче", "Ready for pickup"), "reserved": ("Зарезервирован", "Reserved"),
           "delayed": ("Задерживается", "Delayed"), "collected": ("Получен", "Collected")}


def exchange_reply(state, draft, text, language, message_id, *, order_number, photo):
    tr = lambda ru, en: localized(language, ru, en)  # noqa: E731
    number = re.search(r"(?:№\s*|\b)(\d{4,9})\b", text)
    if number and int(number[1]) != order_number:
        return Reply(tr("Заказ не подтверждён для этого диалога.", "That order is not verified for this conversation."))
    if photo or re.search(r"поврежд|дефект|сломал|defect|damag", text):
        return Reply(tr(f"Передаю заказ № {order_number} сотруднику на проверку повреждения.",
                        f"I’m handing order {order_number} to a specialist to review the damage."), handoff=True)
    customer = "andrey-after-purchase"
    order = find_order(state, customer=customer, order_number=order_number)
    if re.search(r"плат[её]ж|деньги|refund", text):
        summary = tr(f"Отдельный возврат оплаты по заказу № {order_number} на {order['total']} ₽.",
                     f"Separate payment refund of RUB {order['total']} for order {order_number}.")
        return Reply(summary + "\n" + confirmation(draft, message_id, {"operation": "refund"}, language))
    size = re.search(r"\b(xl|m|l)\b", text)
    if size:
        draft["targetSize"] = size[1].upper()
    elif re.search(r"статус|где заказ|status|where", text):
        return _shipment(state, customer, order_number, language)
    if not draft.get("targetSize"):
        return Reply(tr(f"Заказ № {order_number} подтверждён. Для обмена укажите нужный размер M, L или XL.",
                        f"Order {order_number} is verified. For an exchange, enter size M, L or XL."))
    options = exchange_options(state, customer=customer, order_number=order_number, target_size=draft["targetSize"])
    if options["outcome"] == "not_eligible":
        if options.get("reason") == "expired":
            return Reply(tr("Срок обмена 14 дней истёк. Если товар повреждён, пришлите фото для сотрудника.",
                            "The 14-day exchange period has expired. If the item is damaged, send a photo for a specialist."))
        return Reply(tr("Обмен возможен после получения заказа и на другой размер.",
                        "An exchange is available after collection and for a different size."))
    if options["outcome"] != "available":
        return Reply(tr("Нужного размера сейчас нет. Могу передать запрос сотруднику.",
                        "That size is out of stock. I can hand the request to a specialist."))
    points = [point for point in options["pickupPoints"] if point["available"]]
    selected = pickup_in(text)
    point = next((item for item in points if item["store"] == selected), None)
    if point is None:
        stock = "\n".join(f"{item['name']} · {item['address']} · {item['available']}" for item in points)
        return Reply(tr("Размер есть в следующих магазинах. Выберите точку обмена.",
                        "This size is available at these stores. Choose a location for your exchange.") + "\n" + stock)
    command = {"operation": "exchange", "target_size": draft["targetSize"], "store": point["store"]}
    summary = tr(f"Обмен {order['name']} с {order['size']} на {draft['targetSize']}. {point['address']}.",
                 f"Exchange {order['name']} from {order['size']} to {draft['targetSize']}. {point['address']}.")
    return Reply(summary + "\n" + confirmation(draft, message_id, command, language))


def _shipment(state, customer, order_number, language):
    shipment = shipment_status(state, customer=customer, order_number=order_number)
    status = localized(language, *_STATUS[shipment["status"]])
    output = [f"№ {order_number} · {status}"]
    if point := shipment.get("pickup"):
        output.append(localized(language, f"{point['address']}. Сегодня до {point['closesAt']}:00.",
                                f"{point['address']}. Open today until {point['closesAt']}:00."))
    if shipment.get("eta"):
        output.append(shipment["eta"])
    elif shipment["status"] == "delayed":
        output.append(localized(language, "Новый срок пока не подтверждён.", "A new date has not been confirmed yet."))
    return Reply("\n".join(output))
