"""Publish report facts from the saved demo conversations and their actual replies."""

from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4

from django.db import connection

from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.domain_event_models import ConversationEventType as Fact
from chatballs.conversations.models import MessageAuthor, SystemEvent

_SETTING = "chatballs.demo_report_generation"


@contextmanager
def historical_facts(dataset):
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [_SETTING, str(dataset.generation)])
    try:
        yield
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config(%s, '', true)", [_SETTING])


def seed_reply_facts(refs, dialog):
    facts = []
    accepted = queued = False
    responsible = None
    latest = dialog.created_at
    for message in dialog.messages.order_by("created_at", "pk"):
        at = message.created_at
        if message.system_event == SystemEvent.AI_HANDED_OVER:
            facts.append(_fact(dialog, Fact.QUEUE_ENTERED, at, actor="AI"))
            queued = True
        if message.author_type == MessageAuthor.OPERATOR:
            if not accepted:
                responsible = message.author_user_id
                if not queued:
                    facts.append(_fact(dialog, Fact.QUEUE_ENTERED, latest, actor="SYSTEM"))
                taken_at = latest + (at - latest) / 2
                facts.append(_fact(dialog, Fact.ACCEPTED, taken_at, actor="HUMAN", user=responsible,
                                   responsible=responsible))
                accepted = True
            facts.append(_fact(dialog, Fact.PUBLIC_REPLY, at, actor="HUMAN", user=message.author_user_id,
                               responsible=responsible))
        elif message.author_type == MessageAuthor.AI:
            facts.append(_fact(dialog, Fact.PUBLIC_REPLY, at, actor="AI"))
        latest = at
    if responsible != dialog.assigned_operator_id:
        if responsible:
            facts.append(_fact(dialog, Fact.TRANSFERRED, latest, actor="HUMAN", user=responsible,
                               responsible=dialog.assigned_operator_id))
        facts.append(_fact(dialog, Fact.ACCEPTED, latest, actor="HUMAN", user=dialog.assigned_operator_id,
                           responsible=dialog.assigned_operator_id))
    for event in ConversationEvent.objects.bulk_create(facts):
        refs.recorder.record(event)


def _fact(dialog, kind, at, *, actor, user=None, responsible=None):
    return ConversationEvent(
        organization_id=dialog.organization_id, conversation=dialog, event_type=kind, occurred_at=at,
        operation_id=uuid4(), actor_kind=actor, initiated_by_id=user, responsible_id=responsible,
        group_id=dialog.group_id, connection_id=dialog.connection_id, transport=dialog.connection.provider,
    )
