"""Contact actions call the same card and owner-only merge operations as HTTP."""

from dataclasses import replace

from chatballs.conversations import contact_services as service
from chatballs.conversations.clients import PROVIDER_BY_CODE
from chatballs.conversations.contact_card import CARD_LIMITS
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import (
    BOOLEAN,
    IDENTIFIER,
    TEXT,
    action,
    enum,
    obj,
    required,
)
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec

CLIENT = replace(obj(id=TypeSpec("integer"), name=TEXT, phone=TEXT, email=TEXT,
    company=TEXT, city=TEXT, description=TEXT), open=True)
CARD = obj(client=CLIENT)
CARD_FIELDS = {name: TypeSpec("string", max_length=limit) for name, limit in CARD_LIMITS.items()}


def result(data):
    return OperationResult(ResultState.COMPLETED, data)


def listing(context, values):
    return result(service.contacts(context.tenant, {key: ("1" if value else "0")
        if isinstance(value, bool) else value for key, value in values.items()}))


def get(context, values):
    context.require_contact(values["contact_id"])
    return result(service.card(context.tenant, values["contact_id"]))


def change(context, values):
    context.require_contact(values["contact_id"])
    return result(service.change_card(context.tenant, values["contact_id"],
        {key: value for key, value in values.items() if key in CARD_FIELDS}))


def merge(context, values):
    return result(service.merge(context.tenant, values["contact_id"], values["sourceId"], values["reason"]))


def unmerge(context, values):
    return result(service.unmerge(context.tenant, values["contact_id"], values["mergeId"], values["reason"]))


for key, title, inputs, output, handler, method, route, view, capability in (
    ("contacts.get", "native.contacts_list", obj(q=TEXT, agent=TypeSpec("array", items=TypeSpec("integer")),
        channel=TypeSpec("array", items=enum(tuple(PROVIDER_BY_CODE), "native.contact_channel")), open=BOOLEAN,
        sort=enum(("open", "activity"), "native.contact_sort"), dir=enum(("asc", "desc"), "native.sort_direction"),
        **PAGE_INPUTS), page_of(CLIENT), listing, "GET", "", "ClientsView", "customers.view"),
    ("contacts.card.get", "native.contact_read", obj(contact_id=replace(IDENTIFIER, title_key="native.fields.contact_id")), CARD, get,
        "GET", "<int:contact_id>/", "ClientDetailView", "customers.view"),
    ("contacts.card.patch", "native.contact_change", obj(contact_id=replace(IDENTIFIER, title_key="native.fields.contact_id"), **CARD_FIELDS), CARD, change,
        "PATCH", "<int:contact_id>/", "ClientDetailView", "customers.manage"),
    ("contacts.merge.post", "native.contacts_merge", obj(contact_id=replace(IDENTIFIER, title_key="native.fields.contact_id"), sourceId=replace(IDENTIFIER, title_key="native.fields.sourceId"),
        reason=required(TEXT)), CARD, merge, "POST", "<int:contact_id>/merge/", "ClientMergeView", "customers.manage"),
    ("contacts.merge.delete", "native.contacts_unmerge", obj(contact_id=replace(IDENTIFIER, title_key="native.fields.contact_id"), mergeId=replace(IDENTIFIER, title_key="native.fields.mergeId"),
        reason=required(TEXT)), CARD, unmerge, "DELETE", "<int:contact_id>/merge/", "ClientMergeView", "customers.manage"),
):
    action(key=key, title=title, input=inputs, output=output, handler=handler, method=method,
        route=f"conversations/clients/{route}", view=f"chatballs.conversations.reporting_views.{view}",
        capability=capability, scope="contact" if handler in {get, change} else "organization")
