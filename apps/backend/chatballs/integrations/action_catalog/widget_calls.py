"""A widget decline is a product command, never an authentication exclusion."""

from chatballs.calls.serializers import public_call_state_payload
from chatballs.calls.services import decline_call_for_identity
from chatballs.integrations.action_catalog.call_schemas import PUBLIC_CALL
from chatballs.integrations.action_catalog.calls import completed
from chatballs.integrations.action_catalog.contracts import NativeAccessDenied
from chatballs.integrations.action_catalog.schema import BOOLEAN, action, obj
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.webchat.session_access import resolved_web_session


def decline(context, values):
    with resolved_web_session(values["credential"],
            expected_organization_id=context.tenant.organization_id) as (_tenant, session):
        if session is None:
            raise NativeAccessDenied("context")
        call = decline_call_for_identity(identity=session.identity,
            expected_conversation_id=context.conversation_id if context.scope != "organization" else None)
        return completed({"ok": True, "call": public_call_state_payload(call)})


action(key="calls.widget_decline.post", title="native.widget_call_decline",
    input=obj(credential=TypeSpec("string", required=True, secret=True,
        title_key="native.web_session_credential")), output=obj(ok=BOOLEAN, call=PUBLIC_CALL),
    handler=decline, capability="", scope="conversation", route="api/v1/webchat/call/decline/",
    view="chatballs.webchat.views.WebchatCallDeclineView", method="POST")
