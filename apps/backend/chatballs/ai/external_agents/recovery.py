"""Best-effort cancellation never changes an already committed terminal receipt."""

import http.client
import json
from functools import partial

from chatballs.ai.execution_policy import execution_guard
from chatballs.ai.external_agents.adapter import clean_address
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.send_guards import cancel_handoff
from chatballs.ai.external_agents.state import lock_conversation
from chatballs.ai.provider.base import ProviderRejected
from chatballs.integrations.adapters.auth import BearerAuth, OutboundRequest
from chatballs.integrations.adapters.contracts import Limits
from chatballs.integrations.adapters.transport import GuardedTransport, TransportError
from chatballs.integrations.outbound import OutboundUrlRejected
from chatballs.integrations.service_connections.binding import load_credentials
from chatballs.tenancy.database import tenant_atomic


def cancel_due(context, conversation_id):
    with tenant_atomic(context):
        if lock_conversation(context, conversation_id) is None:
            return
        rows = ExternalAgentRequest.objects.select_for_update().filter(
            conversation_id=conversation_id, cancel_pending=True,
        ).select_related("session__connection__integration")
        plans = []
        for row in rows:
            connection = row.session.connection
            service = connection.integration.service_settings
            row.cancel_pending = False
            row.save(update_fields=["cancel_pending"])
            if connection.integration.runtime_revision != row.authorization_versions["integration"]:
                continue
            body = {"version": "1", "requestId": str(row.public_id),
                    "reason": "expired" if row.reason_code == "deadline_exceeded" else "control_revoked"}
            plan = OutboundRequest("POST", clean_address(service.settings["base_url"]) +
                                   f"/requests/{row.public_id}/cancel", headers={"Content-Type": "application/json"},
                                   body=json.dumps(body).encode())
            plans.append((connection.pk, row.authorization_versions, BearerAuth().prepare(plan, load_credentials(service), {})))
    for connection_id, versions, plan in plans:
        try:
            with execution_guard(partial(cancel_allowed, context, connection_id, versions)):
                GuardedTransport().send(plan, limits=Limits(timeout_seconds=10, max_response_bytes=262144,
                                                           max_file_bytes=262144))
        except (ProviderRejected, TransportError, OutboundUrlRejected, OSError, http.client.HTTPException):
            pass


def cancel_allowed(context, connection_id, versions):
    try:
        with cancel_handoff(context, connection_id, versions):
            return True
    except ProviderRejected:
        return False
