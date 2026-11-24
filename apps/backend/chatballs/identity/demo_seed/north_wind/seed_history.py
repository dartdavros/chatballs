"""Store the prepared exchange as ordinary Chatballs messages and attachments."""

from datetime import timedelta
from uuid import uuid4

from django.utils.formats import date_format
from django.utils.translation import override

from chatballs.ai.skill_templates.order_basis import CARD_ID, STATUS_ID
from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.inbound_media import _store_attachment
from chatballs.conversations.models import Message, MessageAuthor, MessageKind, SystemEvent
from chatballs.conversations.transports.base import InboundFile
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate
from chatballs.identity.demo_seed.north_wind.appointments import MOSCOW
from chatballs.identity.demo_seed.north_wind.history_skills import (
    card_data,
    history_template_id,
    snapshot_fields,
)
from chatballs.identity.demo_seed.north_wind.proposal_document import proposal_path, render_proposal
from chatballs.identity.demo_seed.north_wind.support_media import seed_team_photo
from chatballs.identity.demo_seed.north_wind.wholesale import quote_party
from chatballs.tenancy.context import TenantContext


def append_history(refs, conversation, rows, at, templates, *, cadence):
    contact_message = conversation.messages.filter(author_type=MessageAuthor.CONTACT).first()
    timestamp = at
    dates = history_dates(refs.language, at)
    for index, (speaker, text) in enumerate(rows, start=2):
        timestamp = at + cadence * index
        if speaker == "checkpoint":
            continue
        if speaker == "snapshot":
            _save_snapshot(refs, conversation, text, timestamp, dates, templates)
            continue
        if isinstance(text, str):
            text = replace_dates(text, dates)
        if speaker == "photo":
            seed_team_photo(conversation, timestamp)
            continue
        if speaker == "note":
            comment = ConversationComment(
                organization=refs.organization, conversation=conversation, author=refs.users["elena"],
                audience="INTERNAL", operation_id=uuid4(), text=text, created_at=timestamp,
            )
            comment.validate_tenant_relations()
            # Import the original timestamp when inserting the append-only entry.
            comment.save_base(raw=True, force_insert=True)
            refs.recorder.record(comment)
            continue
        fields = _message(refs, speaker, text, contact_message)
        message = Message.objects.create(conversation=conversation, **fields)
        if speaker in {"catalogue", "proposal"}:
            _attach(refs, message, speaker, timestamp)
        backdate(message, timestamp)
        if speaker == "customer":
            contact_message = message
    backdate(conversation, timestamp, "last_message_at", "last_activity_at")


def _message(refs, speaker, text, contact_message):
    if speaker in {"card", "status", "card-order", "status-order"}:
        return _formatted_message(refs, speaker, text)
    if speaker in {"tool", "tool-error", "tool-timeout"}:
        error = {"tool-error": "not_found", "tool-timeout": "timeout"}.get(speaker, "")
        return {"author_type": MessageAuthor.SYSTEM, "system_event": SystemEvent.TOOL_CALLED,
                "system_params": {"tool": text, "result": "error" if error else "ok", "error": error,
                                  "durationMs": 170,
                                  "turnId": contact_message.pk if contact_message else None}}
    if speaker == "handoff":
        return {"author_type": MessageAuthor.SYSTEM, "system_event": SystemEvent.AI_HANDED_OVER}
    if speaker == "claimed":
        return {"author_type": MessageAuthor.SYSTEM, "system_event": SystemEvent.OPERATOR_TOOK,
                "system_params": {"operator": refs.users["anna"].full_name}}
    if speaker == "joined":
        return {"author_type": MessageAuthor.SYSTEM, "system_event": SystemEvent.SPECIALIST_JOINED,
                "system_params": {"operator": refs.users[text].full_name}}
    if speaker in {"catalogue", "proposal"}:
        return {"author_type": MessageAuthor.AI, "kind": MessageKind.FILE, "text": text}
    author = {"customer": MessageAuthor.CONTACT, "agent": MessageAuthor.AI, "system": MessageAuthor.SYSTEM}
    return {"author_type": author.get(speaker, MessageAuthor.OPERATOR), "text": text,
            "author_user": None if speaker in author else refs.users[speaker]}


def _formatted_message(refs, speaker, value):
    number = value if speaker == "card-order" else value["order"] if speaker == "status-order" else "2042"
    dataset = refs.recorder.dataset
    order = dataset.shop_state["sampleOrders"][number]
    skill = refs.order_skill
    is_card = speaker.startswith("card")
    template_id = history_template_id(dataset, CARD_ID if is_card else STATUS_ID)
    template = next(item for item in skill.templates if item["id"] == template_id)
    values = {"order_no": str(order["number"])}
    if is_card:
        total = order["total"]
        values.update(total=total, items=[{"title": order["name"], "qty": 1, "price": total, "sum": total}])
    elif isinstance(value, dict):
        values.update({key: value[key] for key in ("status", "eta") if key in value})
    else:
        values["status"] = value
    return {"author_type": MessageAuthor.AI, **snapshot_fields(skill, template, values, refs.language)}


def _attach(refs, message, kind, timestamp):
    if kind == "proposal":
        quote = quote_party(refs.recorder.dataset.shop_state, product_id="alpine",
                            quantities={"M": 6, "L": 10, "XL": 4}, city="kazan", budget=35000)
        proposal = {"number": "KP-205", "quote": quote, "company": message.conversation.contact.name,
                    "validUntil": (timestamp + timedelta(days=7)).isoformat(),
                    "email": "school@severny-veter.test", "contact": "Ольга" if refs.language == "ru" else "Olga",
                    "address": "Казань, ул. Спортивная, 12" if refs.language == "ru" else "12 Sportivnaya Street, Kazan"}
        name, mime = "KP-205.html", "text/html"
        content = render_proposal(proposal, refs.language).encode()
    else:
        name, mime = f"north-wind-catalogue-{refs.language}.pdf", "application/pdf"
        content = manifest.media_bytes(name)
    _store_seed_file(message, name, mime, content)


def history_dates(language, at):
    local = at.astimezone(MOSCOW)
    with override(language):
        return {"fitting_date": date_format(local + timedelta(days=1), "j E"),
                "later_date": date_format(local + timedelta(days=2), "j E"),
                "valid_until": date_format(local + timedelta(days=7), "j E Y")}


def replace_dates(text, dates):
    for key, replacement in dates.items():
        text = text.replace("{" + key + "}", replacement)
    return text


def _save_snapshot(refs, conversation, item, timestamp, dates, templates):
    skill, template = templates[item["template"]]
    values = card_data(item)
    rows = values.pop("rows")
    values = {key: replace_dates(value, dates) for key, value in values.items()}
    values["rows"] = [{key: replace_dates(value, dates) for key, value in row.items()} for row in rows]
    fields = snapshot_fields(skill, template, values, refs.language)
    photo, document = item.get("photo"), item.get("document")
    message = Message.objects.create(conversation=conversation, author_type=MessageAuthor.AI,
                                     kind=MessageKind.FILE if photo or document else MessageKind.TEXT, **fields)
    if photo:
        _store_seed_file(message, f"{item['title']}.jpg", "image/jpeg",
                         manifest.media_bytes(f"north-wind-{photo}.jpg"))
    if document:
        _save_document(refs, message, document, timestamp)
    backdate(message, timestamp)


def _save_document(refs, message, options, timestamp):
    dataset = refs.recorder.dataset
    quote = quote_party(dataset.shop_state, product_id=options["model"],
                        quantities={"M": 6, "L": 10, "XL": 4}, city=options["city"], budget=35000)
    proposal = {"number": options["number"], "quote": quote, "company": options["company"],
                "validUntil": (timestamp + timedelta(days=7)).isoformat(),
                "email": options["email"], "contact": options["contact"], "address": options["address"]}
    _store_seed_file(message, f"{proposal['number']}.html", "text/html", render_proposal(proposal, refs.language).encode())
    dataset.shop_state.setdefault("historyProposals", {})[proposal["number"]] = proposal
    tenant = TenantContext.for_resource(refs.organization)
    message.template_snapshot["documentPath"] = proposal_path(tenant, dataset.generation, proposal["number"], history=True)
    message.save(update_fields=["template_snapshot"])


def _store_seed_file(message, name, mime, content):
    _store_attachment(message.conversation.connection, InboundFile(
        name=name, content_type=mime, size=len(content), content=content,
    ), message)
    if not message.attachment:
        raise RuntimeError(f"Could not store demo attachment {name}")
