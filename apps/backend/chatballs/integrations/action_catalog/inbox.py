"""Read operations reuse the product's visibility and bounded query services."""

from chatballs.conversations.activity_queries import conversation_activity
from chatballs.conversations.counter_queries import conversation_counters
from chatballs.conversations.directory_queries import conversation_directory
from chatballs.conversations.journal_queries import participation_journal
from chatballs.conversations.visitor_state_queries import visitor_state
from chatballs.integrations.action_catalog.inbox_schemas import (
    ACTIVITY,
    COUNTERS,
    DIRECTORY,
    HISTORY_KIND,
    JOURNAL,
    VISITORS,
)
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import CONVERSATION_ID, TEXT, action, obj
from chatballs.integrations.adapters.contracts import OperationResult, ResultState


def counters(context, values):
    return OperationResult(ResultState.COMPLETED, conversation_counters(context.tenant))


def directory(context, values):
    return OperationResult(ResultState.COMPLETED, conversation_directory(context.tenant, values))


def activity(context, values):
    return OperationResult(ResultState.COMPLETED, conversation_activity(context.tenant, values["conversation_id"], values))


def journal(context, values):
    return OperationResult(ResultState.COMPLETED, participation_journal(context.tenant, values["conversation_id"], values))


def visitors(context, values):
    return OperationResult(ResultState.COMPLETED, visitor_state(context.tenant, values["conversation_id"]))


for key, title, inputs, output, handler, route, module, view, scope in (
    ("conversations.counters.get", "native.inbox_counters", obj(), COUNTERS, counters,
        "counters/", "counter_views", "ConversationCountersView", "organization"),
    ("conversations.directory.get", "native.inbox_directory", obj(q=TEXT), DIRECTORY, directory,
        "directory/", "directory_views", "ConversationDirectoryView", "organization"),
    ("conversations.activity.get", "native.inbox_activity", obj(conversation_id=CONVERSATION_ID,
        kind=HISTORY_KIND, **PAGE_INPUTS), page_of(ACTIVITY), activity,
        "<int:conversation_id>/activity-history/", "activity_views", "ConversationActivityView", "conversation"),
    ("conversations.participation_journal.get", "native.inbox_journal", obj(conversation_id=CONVERSATION_ID,
        kind=HISTORY_KIND, **PAGE_INPUTS), page_of(JOURNAL), journal,
        "<int:conversation_id>/participation-journal/", "participation_journal", "ParticipationJournalView", "conversation"),
    ("conversations.visitor_state.get", "native.inbox_visitors", obj(conversation_id=CONVERSATION_ID), VISITORS, visitors,
        "<int:conversation_id>/visitor-state/", "visitor_state_views", "VisitorStateView", "conversation"),
):
    action(key=key, title=title, input=inputs, output=output, handler=handler, method="GET", capability="conversations.view",
        scope=scope, route=f"conversations/{route}", view=f"chatballs.conversations.{module}.{view}")
