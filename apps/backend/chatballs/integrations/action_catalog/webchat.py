"""The site source can request one normal, consent-bound autonomous reply."""

from chatballs.integrations.action_catalog.schema import action, labelled_codes, obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.schema import TypeSpec


def first_reply(context, values):
    from chatballs.webchat.proactive import execute
    return execute(context, values)


action(key="webchat.first_reply", title="site_events.first_reply",
    input=obj(instruction=TypeSpec("string", required=True, max_length=4000, title_key="site_events.instruction")),
    output=obj(state=labelled_codes(("sent", "suppressed"), "site_events.state", "site_events.state.unknown"),
        messageId=TypeSpec("string", nullable=True, title_key="site_events.message")),
    handler=first_reply, capability="conversations.operate", scope="conversation", execution="io", effect=Effect.CREATE,
    route="api/v1/webchat/site-events/", view="chatballs.webchat.site_event_views.WebchatSiteEventView", method="POST")
