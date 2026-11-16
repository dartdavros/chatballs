"""Fresh authority and a short serialized handoff; response waits hold no locks."""

from contextlib import contextmanager

from django.http import Http404
from django.utils import timezone

from chatballs.ai.external_agents.config_models import ExternalAgentConnection
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.formatted_replies import TemplateConflict
from chatballs.ai.external_agents.normalization import current as content_current
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.ai.external_agents.state import applicable, lock_conversation
from chatballs.ai.provider.base import ProviderRejected
from chatballs.tenancy.database import tenant_atomic


@contextmanager
def request_handoff(work, context):
    with tenant_atomic(context):
        stub = ExternalAgentRequest.objects.filter(public_id=work.request_id).first()
        if stub is None or lock_conversation(context, stub.conversation_id) is None:
            raise ProviderRejected("autonomous turn cancelled")
        row = ExternalAgentRequest.objects.select_related("session__connection").get(pk=stub.pk)
        permitted = (row.active and row.fence == work.fence
                and row.state in ("dispatching", "accepted", "processing")
                and row.lease_until is not None and row.lease_until > timezone.now()
                and applicable(row, context))
        if not permitted:
            raise ProviderRejected("autonomous turn cancelled")
        yield


@contextmanager
def delivery_handoff(item_id, context, conversation_id):
    with tenant_atomic(context):
        if lock_conversation(context, conversation_id) is None:
            raise ProviderRejected("autonomous turn cancelled")
        item = ExternalAgentDeliveryItem.objects.select_related("delivery__request__session__connection").filter(pk=item_id).first()
        permitted = (item is not None and item.sending and item.state == "queued"
                and item.delivery.request.active and item.delivery.request.state == "delivering"
                and applicable(item.delivery.request, context))
        if not permitted:
            raise ProviderRejected("autonomous turn cancelled")
        try:
            content_current(item.message, item.delivery.request)
        except (ValueError, Http404, TemplateConflict) as error:
            raise ProviderRejected("autonomous turn cancelled") from error
        yield


def request_current(work, context):
    try:
        with request_handoff(work, context):
            return True
    except ProviderRejected:
        return False


def delivery_current(item_id, context, conversation_id):
    try:
        with delivery_handoff(item_id, context, conversation_id):
            return True
    except ProviderRejected:
        return False


@contextmanager
def cancel_handoff(context, connection_id, versions):
    from chatballs.identity.operation_modes import lock_organization

    with tenant_atomic(context):
        organization = lock_organization(context.organization_id)
        connection = ExternalAgentConnection.objects.select_related("integration").filter(pk=connection_id).first()
        if (connection is None or not organization.external_execution_enabled or not connection.enabled
                or not connection.integration.is_active or connection.revision != versions["configuration"]
                or connection.credential_version != versions["credential"]
                or connection.integration.runtime_revision != versions["integration"]):
            raise ProviderRejected("autonomous turn cancelled")
        yield
