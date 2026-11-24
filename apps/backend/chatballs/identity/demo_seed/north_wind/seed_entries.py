"""Prepared inbox starting points for the North Wind scenarios."""

from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.models import (
    Contact,
    ControlMode,
    Conversation,
    Message,
)
from chatballs.conversations.participant_models import ConversationParticipant
from chatballs.identity.demo_seed import manifest
from chatballs.identity.demo_seed.loaders.common import backdate
from chatballs.identity.demo_seed.north_wind.delivery_scenarios import (
    create_delivery_queue,
    load_delivery_scenarios,
)
from chatballs.identity.demo_seed.north_wind.history_skills import load_history_skills
from chatballs.identity.demo_seed.north_wind.report_history import (
    historical_facts,
    seed_reply_facts,
)
from chatballs.identity.demo_seed.north_wind.seed_history import append_history
from chatballs.identity.demo_seed.north_wind.support_media import (
    prepare_support_dialog,
    seed_team_photo,
)
from chatballs.identity.demo_seed.north_wind.weekly_report import seed_weekly_report


def load_entries(refs):
    if not refs.recorder:
        return
    data = manifest.load("north_wind", refs.language)
    history_data = manifest.load("north_wind_history", refs.language)
    history = history_data["dialogues"]
    dataset = refs.recorder.dataset
    dataset.shop_state["historyLanguage"] = refs.language
    now = timezone.now()
    templates = load_history_skills(refs, history_data["skills"], history)
    with historical_facts(dataset):
        dialogs = _load_histories(refs, data, history, templates, now)
    seed_weekly_report(dataset, dialogs, now)
    dataset.save(update_fields=["shop_state"])


def _load_histories(refs, data, history, templates, now):
    dataset = refs.recorder.dataset
    local_tools = dataset.shop_state.get("localTools")
    delivery_inbox = create_delivery_queue(refs, data["deliveryAutomation"])
    dialogs = []
    for index, entry in enumerate(data["entries"], start=1):
        at = now - timedelta(minutes=7 + index * 2)
        key = entry["key"]
        group = delivery_inbox[0] if key == "delivery" else refs.groups[entry["group"]]
        conversation = _conversation(refs, entry, group, at)
        dialogs.append(conversation)
        widget = _entry_widget(key, entry)
        if local_tools and (widget or key == "team"):
            prepare_support_dialog(dataset, key, conversation)
        if local_tools and widget:
            binding = dataset.shop_state["supportDialogs"][key]
            binding["widgetKey"] = refs.widgets[widget].public_key
            if "orderNumber" in entry:
                binding["orderNumber"] = entry["orderNumber"]
        if local_tools and key == "formatted-external":
            dataset.shop_state["externalExecutor"]["conversationId"] = conversation.pk
        if local_tools and key == "proposal":
            dataset.shop_state["proposalDialog"] = {"conversationId": conversation.pk, "managerId": refs.users["elena"].pk}
        if key == "team":
            seed_team_photo(conversation, at + timedelta(seconds=5))
            _team(refs, conversation, data["teamComments"], at)
        if key == "delivery":
            conversation.labels.add(delivery_inbox[1])
            if local_tools:
                load_delivery_scenarios(refs, conversation, data["deliveryAutomation"], inbox=delivery_inbox)
        append_history(refs, conversation, history[key], at, templates)
        seed_reply_facts(refs, conversation)
    return dialogs


def _conversation(refs, entry, group, at):
    organization = refs.organization
    if entry["key"] == "team":
        connection_key = "tg"
    else:
        connection_key = _entry_widget(entry["key"], entry) or "web"
    connection = refs.integrations[connection_key]
    contact = Contact.objects.create(organization=organization, name=entry["customer"])
    conversation = Conversation.objects.create(
        organization=organization, contact=contact, channel=connection.channel, connection=connection,
        external_chat_id=f"north-wind:{refs.recorder.dataset.generation}:{entry['key']}",
        group=group, assigned_operator=refs.users[entry["responsible"]], assigned_at=at,
        control_mode=ControlMode.HUMAN, priority=entry["priority"], expected_responder=entry["awaiting"],
    )
    backdate(conversation, at, "created_at", "last_activity_at", "last_message_at")
    if entry.get("question"):
        message = Message.objects.create(conversation=conversation, author_type="CONTACT", text=entry["question"])
        backdate(message, at)
    conversation.labels.add(*(refs.labels[key] for key in entry["labels"]))
    refs.recorder.protect_conversation(conversation)
    return conversation


def _entry_widget(key, entry):
    if key in {"fitting", "proposal"}:
        return "web"
    if key in {"delivery", "formatted", "formatted-external"} or entry.get("orderNumber"):
        return "web_help"
    return None


def _team(refs, conversation, comments, at):
    for offset, (key, text) in enumerate(zip(("svetlana", "igor"), comments, strict=True), start=1):
        membership = refs.memberships[key]
        participant = ConversationParticipant.objects.create(
            organization=refs.organization, conversation=conversation, membership=membership,
            joined_by=refs.memberships["anna"], join_reason=text,
        )
        ConversationComment.objects.create(
            organization=refs.organization, conversation=conversation, author=membership.user,
            audience="INTERNAL", text=text, operation_id=uuid4(),
        )
        backdate(participant, at + timedelta(seconds=5 + offset), "joined_at")
