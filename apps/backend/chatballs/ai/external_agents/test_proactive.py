"""Idle-only initiative, atomic rejection, replay and shared native delivery."""

from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from django.db import transaction

from chatballs.ai.external_agents.delivery_models import (
    ExternalAgentDelivery,
    ExternalAgentDeliveryItem,
)
from chatballs.ai.external_agents.media_testing import MediaCase
from chatballs.ai.external_agents.operation_models import ExternalAgentOperation
from chatballs.ai.external_agents.operation_testing import OperationData, image_bytes
from chatballs.ai.external_agents.request_models import ExternalAgentRequest
from chatballs.channels.models import Channel
from chatballs.conversations.models import Contact, Conversation, Message
from chatballs.identity.models import Organization


class ProactiveTests(OperationData, MediaCase):
    def test_busy_rejection_has_no_effect_and_same_request_can_later_succeed(self):
        row = self.prepare_session(complete=False)
        body = self.operation_body()
        counts = (Message.objects.count(), ExternalAgentDelivery.objects.count())
        for active in (False, True):
            if active:
                self.claim()
            response = self.post_operation(body)
            self.assertEqual(response.status_code, 409, response.content)
            self.assertEqual(response.json()["error"]["code"], "conversation_busy")
            self.assertEqual((Message.objects.count(), ExternalAgentDelivery.objects.count()), counts)
            self.assertFalse(ExternalAgentOperation.objects.exists())
        result = self.result(row)
        result["externalSessionId"] = None
        self.accept(row, result)
        self.deliver()
        response = self.post_operation(body)
        self.assertEqual(response.status_code, 202, response.content)
        self.assertIsNone(ExternalAgentRequest.objects.latest("pk").trigger_id)
        self.deliver()
        replay = self.post_operation(body)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json(), response.json())

    def test_disabled_closed_foreign_and_strict_contract(self):
        self.prepare_session(proactive=False)
        body = self.operation_body()
        before = Message.objects.count()
        response = self.post_operation(body)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ExternalAgentOperation.objects.exists())
        for field, value in (("organizationId", str(self.organization.pk)), ("recipient", "elsewhere")):
            self.assertEqual(self.post_operation({**body, field: value}).status_code, 400)
        self.assertEqual(self.post_operation(body, HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code, 400)
        self.assertEqual(self.post_operation({**body, "agentId": str(2**63)}).status_code, 400)
        self.assertEqual(self.post_operation({**body, "agentId": str(self.agent.pk + 999)}).status_code, 404)
        other = Organization.objects.create(name="Foreign", slug="proactive-foreign")
        channel = Channel.objects.create(organization=other, name="Other", code="other")
        contact = Contact.objects.create(organization=other, name="Other")
        foreign = Conversation.objects.create(organization=other, channel=channel, contact=contact)
        self.assertEqual(self.post_operation(body, conversation_id=foreign.pk).status_code, 404)
        for state in ("CLOSED", "SPAM"):
            Conversation.objects.filter(pk=self.conversation.pk).update(lifecycle=state)
            self.assertEqual(self.post_operation(body).status_code, 403)
        self.assertEqual(Message.objects.count(), before)
        self.assertFalse(ExternalAgentOperation.objects.exists())

    def test_batch_validation_replay_digest_and_no_client_overtaking(self):
        self.prepare_session()
        body = self.operation_body()
        body["messages"] *= 2
        count = Message.objects.count()
        self.assertEqual(self.post_operation(body).status_code, 400)
        self.assertEqual(Message.objects.count(), count)
        self.assertFalse(ExternalAgentOperation.objects.exists())
        body["messages"] = body["messages"][:1]
        accepted = self.post_operation(body)
        self.assertEqual(accepted.status_code, 202, accepted.content)
        changed = deepcopy(body)
        changed["messages"][0]["content"]["text"] = "Different"
        self.assertEqual(self.post_operation(changed).status_code, 409)
        incoming = self.request("Client priority")
        self.assertIsNone(self.claim())
        self.deliver()
        self.assertEqual(self.claim().request_id, str(incoming.public_id))
        self.assertEqual(self.post_operation(body).json(), accepted.json())

    def test_all_outgoing_formats_share_normalization_publication_and_transport(self):
        from chatballs.ai.models import Skill
        from chatballs.ai.template_runtime_testing import reply_template

        template = reply_template()
        Skill.objects.create(organization=self.organization, name="Card", description="Description",
                             instruction="Instruction", templates=[template])
        self.bind(self.connection.pk, templateIds=[template["id"]])
        row = self.prepare_session()
        uploaded = self.upload(row).json()
        image = self.upload(row, image_bytes(), name="image.png", mime="image/png").json()
        contents = [{"type": "text", "text": "Text"}, self.file_content(uploaded),
                    {**self.file_content(image), "type": "image"}, {"type": "contact_request"},
                    {"type": "formatted", "templateId": template["id"], "templateRevision": 1,
                     "data": {"title": "Snapshot", "amount": 0, "active": False}}]
        body = self.operation_body(messages=[{"itemId": str(uuid4()), "content": item} for item in contents])
        accepted = self.post_operation(body)
        self.assertEqual(accepted.status_code, 202, accepted.content)
        with patch("chatballs.conversations.transports.send_file", return_value=True) as files, \
             patch("chatballs.conversations.transports.send_contact_request", return_value=True) as contact:
            self.deliver(times=6)
        self.assertEqual(files.call_count, 2)
        self.assertEqual(contact.call_count, 1)
        items = ExternalAgentDeliveryItem.objects.filter(delivery__public_id=body["deliveryId"])
        self.assertEqual(list(items.values_list("state", flat=True)), ["transport_accepted"] * 5)
        self.assertEqual(self.post_operation(body).json(), accepted.json())

    def test_partial_unknown_prevents_overtaking_and_takeover_suppresses_remainder(self):
        self.prepare_session()
        body = self.operation_body(messages=[{"itemId": str(uuid4()), "content": {"type": "text", "text": "Part"}}
                                             for _ in range(3)])
        self.assertEqual(self.post_operation(body).status_code, 202)
        self.sender.side_effect = [True, False]
        self.deliver(times=3)
        rows = ExternalAgentDeliveryItem.objects.filter(delivery__public_id=body["deliveryId"])
        self.assertEqual(list(rows.values_list("state", flat=True)), ["transport_accepted", "unknown", "queued"])
        self.assertEqual(self.post_operation(self.operation_body()).status_code, 409)
        Conversation.objects.filter(pk=self.conversation.pk).update(control_mode="HUMAN")
        self.deliver()
        self.assertEqual(list(rows.values_list("state", flat=True)), ["transport_accepted", "unknown", "suppressed"])
        self.assertEqual(self.post_operation(body).status_code, 403)

    def test_checkpoint_retention_does_not_remove_existing_conversation_route(self):
        row = self.prepare_session()
        ExternalAgentRequest.objects.filter(pk=row.pk).delete()
        response = self.post_operation(self.operation_body())
        self.assertEqual(response.status_code, 202, response.content)
        self.deliver()
        self.assertEqual(self.sender.call_args.kwargs["chat_id"], self.conversation.external_chat_id)

    def test_feature_disable_reenable_and_agent_change_do_not_revive_authority(self):
        from chatballs.ai.models import AIAgent

        self.prepare_session()
        body = self.operation_body()
        before = Message.objects.count()
        with transaction.atomic():
            Organization.objects.filter(pk=self.organization.pk).update(external_execution_enabled=False)
            self.assertEqual(self.post_operation(body).status_code, 403)
            self.agent.refresh_from_db()
            self.assertEqual(self.agent.execution_mode, "external")
            Organization.objects.filter(pk=self.organization.pk).update(external_execution_enabled=True)
            self.assertEqual(self.post_operation(body).status_code, 403)
            transaction.set_rollback(True)
        AIAgent.objects.filter(pk=self.agent.pk).update(execution_mode="builtin")
        self.assertEqual(self.post_operation(body).status_code, 403)
        AIAgent.objects.filter(pk=self.agent.pk).update(execution_mode="external")
        self.assertEqual(self.post_operation(body).status_code, 403)
        self.assertEqual(Message.objects.count(), before)
        self.assertFalse(ExternalAgentOperation.objects.exists())

    def test_web_proactive_commits_native_command_after_real_consent_guard(self):
        from chatballs.conversations.models import ConnectionIdentity
        from chatballs.i18n import t
        from chatballs.webchat.consent import current_version, record_acceptance
        from chatballs.webchat.models import WebSession
        from chatballs.webchat.testing import create_web_widget

        self.bind(self.connection.pk, proactiveEnabled=True)
        self.organization.refresh_from_db()
        self.channel.organization = self.organization
        widget = create_web_widget(self.channel)
        widget.consent_config = {"consent_text": "External execution consent", "consent_version": "v2"}
        widget.save(update_fields=["consent_config"])
        self.conversation.connection = widget.integration
        self.conversation.save(update_fields=["connection"])
        identity = ConnectionIdentity.objects.create(contact=self.contact, connection=widget.integration,
                                                     external_user_id="web-test")
        web = WebSession.objects.create(connection=widget.integration, identity=identity, widget=widget,
                                        token_hash="a" * 64)
        web = WebSession.objects.select_related("widget__integration__channel__ai_agent").get(pk=web.pk)
        record_acceptance(web, version=current_version(web.widget), fields={})
        self.prepare_session()
        body = self.operation_body(messages=[{"itemId": str(uuid4()), "content": {"type": "contact_request"}}])
        response = self.post_operation(body)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual((response.json()["requestId"], response.json()["state"]), (None, "transport_accepted"))
        self.assertEqual(Message.objects.latest("pk").text, t("conversations.contact_request_web", language="ru"))
        self.sender.assert_not_called()
        before = Message.objects.count()
        widget.consent_config = {"consent_text": "Changed", "consent_version": "v3"}
        widget.save(update_fields=["consent_config"])
        self.assertEqual(self.post_operation(self.operation_body()).status_code, 403)
        self.assertEqual(Message.objects.count(), before)
