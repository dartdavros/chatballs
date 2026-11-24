"""Run the local shop dialogue under the native turn and generation locks."""

from datetime import datetime

from django.utils import timezone

from chatballs.conversations.models import AiTurnState, ConnectionIdentity
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.after_sales import refund_payment, request_exchange
from chatballs.identity.demo_seed.north_wind.appointments import book_fitting
from chatballs.identity.demo_seed.north_wind.catalog import PRODUCTS
from chatballs.identity.demo_seed.north_wind.dialogue_exchange import exchange_reply
from chatballs.identity.demo_seed.north_wind.dialogue_fitting import fitting_reply
from chatballs.identity.demo_seed.north_wind.dialogue_input import (
    Reply,
    confirmation_requested,
    confirmed,
    localized,
)
from chatballs.identity.demo_seed.north_wind.dialogue_proposal import proposal_reply
from chatballs.identity.demo_seed.north_wind.local_access import local_demo_enabled
from chatballs.identity.demo_seed.north_wind.proposal_workflow import (
    proposal_result,
    submit_proposal,
)
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write
from chatballs.identity.demo_seed.north_wind.storefront_artifacts import storefront_artifacts
from chatballs.tenancy.database import tenant_atomic

ROUTES = {"fitting": "olga", "proposal": "school", "exchange": "andrey-after-purchase",
          "exchange-expired": "andrey-after-purchase", "exchange-ready": "andrey-after-purchase",
          "exchange-delayed": "andrey-after-purchase", "exchange-refund": "andrey-after-purchase"}


def scope_for(turn, context):
    connection = turn.conversation.connection
    if not (local_demo_enabled() and connection and connection.provider == "WEB"
            and (connection.config.get("northWindStorefront") or connection.config.get("northWindSupport"))):
        return None
    dataset = DemoDataset.objects.filter(
        organization_id=context.organization_id, generation=connection.config.get("demoGeneration"),
        status=DemoDatasetStatus.INSTALLED,
    ).first()
    if dataset is None:
        return None
    for key, binding in dataset.shop_state.get("supportDialogs", {}).items():
        if (key in ROUTES and binding["conversationId"] == turn.conversation.pk and binding["connectionId"] == connection.pk
                and ConnectionIdentity.objects.filter(pk=binding["identityId"], contact_id=turn.conversation.contact_id,
                    connection_id=connection.pk, external_user_id=turn.user_id).exists()):
            return dataset, key, binding
    return None


def try_reply(turn, context):
    from chatballs.conversations.ai_turn_completion import refresh_turn_control
    from chatballs.conversations.ai_turn_result import store_answer

    with tenant_atomic(context):
        if scope_for(turn, context) is None:
            return None
        with storefront_artifacts(turn.conversation.connection) as current:
            if not current or not refresh_turn_control(turn, context):
                return ""
            scope = scope_for(turn, context)
            if scope is None:
                return ""
            dataset, route, binding = scope
            key = str(turn.conversation.pk)
            draft = dataset.shop_state.get("dialogueDrafts", {}).get(key, {})
            if turn.message.pk <= draft.get("lastMessage", 0):
                turn.message.ai_turn_state = AiTurnState.DONE
                turn.message.save(update_fields=["ai_turn_state"])
                return ""
            outcome = _reply(turn, context, dataset, route, binding, draft)
            draft["lastMessage"] = turn.message.pk
            dataset.refresh_from_db(fields=["shop_state"])
            dataset.shop_state.setdefault("dialogueDrafts", {})[key] = draft
            dataset.save(update_fields=["shop_state"])
            return store_answer(turn=turn, context=context, text=outcome.text,
                                handoff=outcome.handoff, document=outcome.document, recommendations=outcome.recommendations,
                                publish_web=outcome.handoff)


def _reply(turn, context, dataset, route, binding, draft):
    text = turn.query.strip()
    lowered = text.casefold()
    language = dataset.shop_state["storefront"]["language"]
    if confirmation_requested(lowered):
        pending = draft.get("confirmation")
        if not confirmed(lowered, pending, turn.message.pk):
            return Reply(localized(language, "Используйте код из последнего сообщения с условиями.",
                                   "Use the code from the latest message with the terms."))
        try:
            return _submit(context, dataset, route, binding, draft, pending, language)
        except ShopError as error:
            draft.pop("confirmation", None)
            if route == "proposal":
                draft.pop("quote", None)
            if route == "fitting" and error.code == "fitting_slot_unavailable":
                return fitting_reply(dataset.shop_state, draft, "", language, turn.message.pk)
            return _failure(error.code, language)
    if route == "proposal" and draft.get("proposal") and lowered in {"статус письма", "mail status"}:
        return _proposal_reply(proposal_result(context, dataset.generation, **draft["proposal"]), language)
    draft.pop("confirmation", None)
    if lowered in {"сотрудник", "оператор", "operator", "specialist"}:
        return Reply(localized(language, "Подключаю сотрудника.", "I’ll connect you with a specialist."), handoff=True)
    if route == "fitting":
        return fitting_reply(dataset.shop_state, draft, lowered, language, turn.message.pk)
    if route == "proposal":
        return proposal_reply(dataset, context, draft, text, language, turn.message.pk)
    return exchange_reply(dataset.shop_state, draft, lowered, language, turn.message.pk,
                          order_number=binding["orderNumber"], photo=bool(turn.message.attachment))


def _submit(context, dataset, route, binding, draft, pending, language):
    command = dict(pending["command"])
    key = f"chat-confirm:{binding['conversationId']}:{pending['messageId']}"
    if route == "proposal":
        result = submit_proposal(context, dataset.generation, key=key, command=command)
        proposal = result["proposal"]
        draft["proposal"] = {"number": proposal["number"], "quote_id": proposal["quoteId"]}
        return _proposal_reply(result, language)
    command.update(customer=ROUTES[route], confirmed=True)
    if route == "fitting":
        if draft.get("bookingCode") != pending["code"] and timezone.now() >= datetime.fromisoformat(command["validUntil"]):
            raise ShopError("quote_changed")
        command.pop("validUntil")
        result = execute_write(context, dataset.generation, book_fitting, key=key, command=command)
        draft["bookingCode"] = pending["code"]
        models = ", ".join(PRODUCTS[product]["name"] for product in result["products"])
        return Reply(localized(language,
            f"Запись № {result['number']} подтверждена. {result['startsAt'][:10]} в {result['startsAt'][11:16]} МСК. {result['address']}. {models}. Бесплатно, {result['minutes']} минут с консультантом.",
            f"Booking {result['number']} confirmed. {result['startsAt'][:10]} at {result['startsAt'][11:16]} Moscow time. {result['address']}. {models}. Free, {result['minutes']} minutes with a consultant."))
    command["order_number"] = binding["orderNumber"]
    refund = command.pop("operation") == "refund"
    result = execute_write(context, dataset.generation, refund_payment if refund else request_exchange, key=key, command=command)
    if refund:
        return Reply(localized(language, f"Возврат № {result['number']} выполнен на {result['amount']} ₽.",
                               f"Refund {result['number']} completed for RUB {result['amount']}."))
    return Reply(localized(language, f"Заявка на обмен № {result['number']} принята. {result['address']}.",
                           f"Exchange request {result['number']} received. {result['address']}."))


def _proposal_reply(result, language):
    from chatballs.i18n import t

    statuses = {"queued": ("Письмо ожидает отправки.", "Email is queued."),
        "sent": ("Письмо отправлено.", "Email sent."), "failed": ("Отправка письма не удалась.", "Email failed."),
        "unknown": ("Исход отправки неизвестен. Сотрудник сверит статус перед повтором.",
                    "Email outcome is unknown. A specialist will check before retrying.")}
    proposal = result["proposal"]
    title = t("north_wind.proposal_title", language=language, number=proposal["number"])
    message = title + "\n" + localized(language, *statuses[result["mail"]["status"]])
    return Reply(message, document={"open": proposal["documentPath"], "download": proposal["downloadPath"],
        "openLabel": localized(language, "Открыть КП", "Open proposal"),
        "downloadLabel": localized(language, "Скачать КП", "Download proposal")})


def _failure(code, language):
    if code in {"stock_unavailable", "fitting_slot_unavailable"}:
        return Reply(localized(language, "Остаток или время изменились. Выберите другой доступный вариант.",
                               "The stock or time changed. Choose another available option."))
    if code in {"quote_changed", "party_stock_unavailable"}:
        return Reply(localized(language, "Условия изменились. Запросите новый расчёт перед подтверждением.",
                               "The terms changed. Ask for a fresh quote before confirming."))
    return Reply(localized(language, "Операцию нельзя выполнить для этого заказа. Подключаю сотрудника.",
                           "That operation is unavailable for this order. I’ll connect you with a specialist."), handoff=True)
