"""Bounded participant lists preserve the original visibility and presence."""

from chatballs.api.pagination import page_payload, paginate
from chatballs.conversations.participant_payloads import participant_payload
from chatballs.conversations.participant_services import participation_history
from chatballs.identity.employee_availability import employee_availability


def active_participants(context, conversation_id):
    rows = list(participation_history(context=context, conversation_id=conversation_id).active())
    availability = employee_availability(context.organization_id, [row.membership for row in rows])
    return {"items": [{**participant_payload(row), **availability[row.membership.user_id]} for row in rows],
        "additionalParticipantLimit": context.organization.additional_participant_limit}


def participant_history(context, conversation_id, params):
    rows = participation_history(context=context, conversation_id=conversation_id)
    return page_payload(paginate(rows, params), participant_payload)
