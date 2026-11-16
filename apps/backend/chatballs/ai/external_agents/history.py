"""Frozen public text history is read only under the current authorization."""


from django.core import signing
from django.http import Http404
from django.utils import timezone

from chatballs.ai.external_agents.auth import authorize_session
from chatballs.ai.external_agents.file_access import issue
from chatballs.ai.external_agents.history_payloads import CURSOR_SALT, page
from chatballs.ai.external_agents.ingress import Conflict
from chatballs.ai.external_agents.json_payloads import size
from chatballs.ai.external_agents.payloads import open_payload
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.conversations.audience_managers import without_suppressed
from chatballs.conversations.models import Message


def read(context, connection, conversation_id, query):
    if not query.get("authorizationId") or not query.get("snapshotCursor"):
        raise ValueError("invalid_request")
    for key in ("snapshotCursor", "pageCursor"):
        value = query.get(key)
        if value is not None and (not isinstance(value, str) or not 1 <= len(value) <= 4096):
            raise ValueError("invalid_request")
    session = authorize_session(context, connection, conversation_id=conversation_id,
                                authorization_id=query.get("authorizationId"), operation="history")
    try:
        signer = signing.Signer(salt=CURSOR_SALT)
        request_id, authorization, offset = signer.unsign_object(query.get("snapshotCursor", ""))
        if offset is not None or authorization != str(session.authorization_id):
            raise ValueError
        page_size = int(query.get("pageSize", "50"))
        if not 1 <= page_size <= 200:
            raise ValueError
        row = ExternalAgentRequest.objects.filter(public_id=request_id, session=session,
                                                 authorization_id=session.authorization_id).first()
        if row is None:
            raise Http404
        if timezone.now() >= row.deadline_at or not row.history_ciphertext:
            raise Conflict(code="snapshot_expired")
        history = open_payload(row.history_ciphertext)
        end = len(history)
        if query.get("pageCursor"):
            page_request, page_authorization, end = signer.unsign_object(query["pageCursor"])
            if (page_request, page_authorization) != (request_id, authorization) or type(end) is not int or not 0 <= end <= len(history):
                raise ValueError
    except (ValueError, TypeError, signing.BadSignature) as error:
        raise ValueError("invalid_request") from error
    existing = set(without_suppressed(Message.including_tests.filter(conversation_id=conversation_id)).values_list("pk", flat=True))
    start = max(0, end - page_size)
    while True:
        items = [item for item in history[start:end] if int(item["id"]) in existing]
        result = page(row, items, start)
        if size(result) <= 262144:
            issue(row, [item["content"] for item in items])
            return result
        start += 1
        if start == end:
            raise ValueError("payload_too_large")
