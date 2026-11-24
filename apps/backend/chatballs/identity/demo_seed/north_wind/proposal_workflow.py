"""Commit the result and send mail through the generation-local mailbox."""

from datetime import timedelta
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone

from chatballs.conversations.comment_models import ConversationComment
from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.i18n import t
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.north_wind.delivery import settle_mail
from chatballs.identity.demo_seed.north_wind.proposal_document import proposal_path
from chatballs.identity.demo_seed.north_wind.state import ShopError, execute_write, read_state
from chatballs.identity.demo_seed.north_wind.wholesale import create_proposal
from chatballs.identity.demo_seed.registry import runtime_recording
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic

PROPOSAL_MAIL = "demo.proposal_mail"
_MAIL_BRANCHES = {
    "school+failed@severny-veter.test": "failed",
    "school+unknown@severny-veter.test": "unknown",
}


def submit_proposal(tenant, generation, *, key, command):
    with tenant_atomic(tenant):
        dataset = DemoDataset.objects.select_for_update().filter(
            organization_id=tenant.organization_id, generation=generation,
            status=DemoDatasetStatus.INSTALLED,
        ).first()
        if dataset is None:
            raise ShopError("demo_generation_unavailable")
        with runtime_recording(dataset):
            proposal = execute_write(tenant, generation, create_proposal, key=key, command=command)
            number = proposal["number"]
            if number not in dataset.shop_state["proposals"]:
                _record_crm_reference(tenant, dataset, proposal)
                enqueue_event(DomainEvent(
                    aggregate_type="demo_proposal", aggregate_id=f"{generation}:{number}",
                    event_type=PROPOSAL_MAIL, payload={"generation": str(generation), "number": number},
                    tenant_context=TenantContext.for_resource(tenant.organization),
                ), available_at=timezone.now() + timedelta(seconds=3))
        return proposal_result(tenant, generation, number=number, quote_id=proposal["quoteId"])


def proposal_result(tenant, generation, *, number, quote_id):
    state = read_state(tenant, generation)
    proposal = state["proposals"].get(number)
    if proposal is None or proposal["quoteId"] != quote_id:
        raise ShopError("proposal_unavailable")
    path = proposal_path(tenant, generation, number)
    return {
        "proposal": {**proposal, "documentPath": path, "downloadPath": f"{path}?download=1"},
        "mail": state["mailbox"][number], "lead": state["crm"][proposal["crmReference"]],
    }


def send_proposal_mail(payload, tenant):
    if tenant is None:
        return
    number = payload["number"]
    try:
        execute_write(
            tenant, payload["generation"], _deliver, key=number, command={"number": number},
        )
    except ShopError as error:
        if error.code != "demo_generation_unavailable":
            raise


def _deliver(state, *, number):
    draft = state["mailbox"].get(number)
    if draft is None or draft["status"] != "queued":
        return draft
    recipient = draft["recipient"]
    result = settle_mail(state, proposal_number=number, status=_MAIL_BRANCHES.get(recipient, "sent"))
    if result["status"] == "sent":
        language = state.get("storefront", {}).get("language", "ru")
        state["channelDeliveries"].append({
            "channel": "EMAIL", "kind": "proposal", "recipient": recipient, "state": "sent", "proposal": number,
            "subject": t("north_wind.proposal_title", language=language, number=number),
            "text": t("north_wind.proposal_mail_body", language=language, number=number),
        })
    return result


def _record_crm_reference(tenant, dataset, proposal):
    binding = dataset.shop_state.get("proposalDialog")
    if not binding:
        return
    crm_id = proposal["crmReference"]
    url = reverse("organization-demo-crm-record", kwargs={
        "organization_public_id": tenant.organization.public_id, "generation": dataset.generation, "reference": crm_id,
    })
    language = dataset.shop_state.get("storefront", {}).get("language", "ru")
    ConversationComment.objects.create(
        organization_id=tenant.organization_id, conversation_id=binding["conversationId"], author_id=binding["managerId"],
        audience="INTERNAL", text=t("north_wind.proposal_crm_note", language=language, number=crm_id, url=url),
        operation_id=uuid4(),
    )
