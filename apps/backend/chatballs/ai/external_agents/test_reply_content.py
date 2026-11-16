"""Native renderer, contact command, atomic batch and delivery checkpoints."""

from copy import deepcopy
from unittest.mock import patch

from chatballs.ai.external_agents import delivery
from chatballs.ai.external_agents.delivery_models import ExternalAgentDeliveryItem
from chatballs.ai.external_agents.formatted_replies import TemplateConflict, catalog
from chatballs.ai.external_agents.media_testing import MediaCase
from chatballs.ai.external_agents.public_messages import public_message
from chatballs.ai.models import Skill
from chatballs.ai.template_runtime_testing import reply_template
from chatballs.conversations.models import Message
from chatballs.i18n import t
from chatballs.tenancy.database import tenant_atomic


class ReplyContentTests(MediaCase):
    def template(self):
        template = reply_template()
        skill = Skill.objects.create(organization=self.organization, name="Skill", description="Description",
                                     instruction="PRIVATE INSTRUCTION", templates=[template])
        self.bind(self.connection.pk, templateIds=[template["id"]])
        return skill, template

    def formatted(self, template, revision=1):
        return {"type": "formatted", "templateId": template["id"], "templateRevision": revision,
                "data": {"title": '<script>alert("x")</script>', "amount": 0, "active": False}}

    def mixed(self, row, file, template):
        body = self.result(row, count=4)
        for item, content in zip(body["outcome"]["messages"], [
            {"type": "text", "text": "first"}, self.file_content(file),
            {"type": "contact_request"}, self.formatted(template)], strict=True):
            item["content"] = content
        return body

    def test_catalog_explicit_native_schema_and_durable_monotonic_revision(self):
        skill, template = self.template()
        row = self.request()
        response = self.client.get(self.root + "reply-templates/", {"authorizationId": str(row.authorization_id)}, **self.header)
        self.assertEqual(response.status_code, 200, response.content)
        item = response.json()["items"][0]
        self.assertEqual(set(item), {"id", "revision", "purpose", "dataSchema", "representations"})
        self.assertEqual(item["dataSchema"], template["schema"])
        self.assertNotIn(b"PRIVATE", response.content)
        initial = item["revision"]
        skill.templates = [{**template, "text": "changed {{ title }}"}]
        skill.save(update_fields=["templates"])
        skill.templates = [template]
        skill.save(update_fields=["templates"])
        self.assertRaises(TemplateConflict, catalog, self.agent.external_binding)
        self.bind(self.connection.pk, templateIds=[template["id"]])
        self.agent.refresh_from_db()
        self.assertEqual(catalog(self.agent.external_binding)["items"][0]["revision"], initial + 2)
        skill.delete()
        Skill.objects.create(organization=self.organization, name="Again", description="Again", instruction="private", templates=[template])
        self.assertRaises(TemplateConflict, catalog, self.agent.external_binding)
        self.bind(self.connection.pk, templateIds=[template["id"]])
        self.agent.refresh_from_db()
        self.assertGreater(catalog(self.agent.external_binding)["items"][0]["revision"], initial + 2)

    def test_invalid_second_item_and_duplicate_ids_publish_nothing(self):
        _, template = self.template()
        row = self.request()
        self.assertIsNotNone(self.claim())
        body = self.result(row, count=2)
        body["outcome"]["messages"][1]["content"] = self.formatted(template, revision=999)
        self.assertEqual(self.callback(row, body).status_code, 409)
        self.assertFalse(Message.objects.filter(author_type="AI").exists())
        body["outcome"]["messages"][1] = deepcopy(body["outcome"]["messages"][0])
        self.assertEqual(self.callback(row, body).status_code, 400)
        self.assertFalse(Message.objects.filter(author_type="AI").exists())

    def test_mixed_batch_snapshots_native_transport_and_idempotent_replay(self):
        skill, template = self.template()
        row = self.request()
        receipt = self.upload(row).json()
        self.assertIsNotNone(self.claim())
        body = self.mixed(row, receipt, template)
        first = self.callback(row, body)
        self.assertEqual(first.status_code, 202, first.content)
        repeat = self.callback(row, body)
        self.assertEqual(repeat.json(), first.json())
        messages = list(Message.objects.filter(author_type="AI").order_by("pk"))
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[2].kind, "contact_request")
        self.assertEqual(messages[2].text, t("conversations.contact_request", language="ru"))
        saved = messages[3].presentation.copy()
        self.assertEqual(saved["sandbox"], "")
        self.assertNotIn('<script>alert', messages[3].content_html)
        self.assertNotIn("srcDoc", str(public_message(messages[3])))
        with patch("chatballs.conversations.transports.send_file", return_value=True) as send_file, \
             patch("chatballs.conversations.transports.send_contact_request", return_value=True) as contact:
            self.deliver(times=5)
        self.assertEqual(send_file.call_count, 1)
        self.assertEqual(contact.call_count, 1)
        self.assertEqual(self.sender.call_count, 2)
        skill.templates = [{**template, "text": "changed {{ title }}"}]
        skill.save(update_fields=["templates"])
        messages[3].refresh_from_db()
        self.assertEqual(messages[3].presentation, saved)
        self.assertEqual(list(ExternalAgentDeliveryItem.objects.values_list("state", flat=True)), ["transport_accepted"] * 4)

    def test_schema_and_source_payload_rejected(self):
        _, template = self.template()
        row = self.request()
        self.claim()
        body = self.result(row)
        content = self.formatted(template)
        content["data"]["amount"] = "not a number"
        body["outcome"]["messages"][0]["content"] = content
        self.assertEqual(self.callback(row, body).status_code, 400)
        content["srcDoc"] = "<script/>"
        self.assertEqual(self.callback(row, body).status_code, 400)

    def test_integral_revision_and_decimal_data_use_native_rendering(self):
        _, template = self.template()
        row = self.request()
        self.claim()
        body = self.result(row)
        content = self.formatted(template, revision=1.0)
        content["data"]["amount"] = 0.5
        body["outcome"]["messages"][0]["content"] = content
        response = self.callback(row, body)
        self.assertEqual(response.status_code, 202, response.content)
        saved = Message.objects.get(author_type="AI")
        self.assertIs(type(saved.template_snapshot["revision"]), int)
        self.assertIn("0,5", saved.text)

    def test_unknown_keeps_fifo_and_takeover_suppresses_remaining_items(self):
        _, template = self.template()
        row = self.request()
        file = self.upload(row).json()
        self.claim()
        self.callback(row, self.mixed(row, file, template))
        self.request("next")
        self.deliver(times=1)
        with patch("chatballs.conversations.transports.send_file", return_value=False) as sender:
            self.deliver(times=3)
        self.assertEqual(sender.call_count, 1)
        self.assertIsNone(self.claim())
        items = list(ExternalAgentDeliveryItem.objects.all())
        self.assertEqual([item.state for item in items], ["transport_accepted", "unknown", "queued", "queued"])
        self.assertEqual(delivery.aggregate(items), "queued")
        self.conversation.control_mode = "HUMAN"
        self.conversation.save(update_fields=["control_mode"])
        self.deliver(times=1)
        self.assertEqual(list(ExternalAgentDeliveryItem.objects.values_list("state", flat=True)),
                         ["transport_accepted", "unknown", "suppressed", "suppressed"])
        self.assertEqual(delivery.aggregate(list(ExternalAgentDeliveryItem.objects.all())), "partial")

    def test_template_changed_between_acceptance_and_send_is_suppressed(self):
        skill, template = self.template()
        row = self.request()
        self.claim()
        body = self.result(row)
        body["outcome"]["messages"][0]["content"] = self.formatted(template)
        self.assertEqual(self.callback(row, body).status_code, 202)
        skill.templates = []
        skill.save(update_fields=["templates"])
        with tenant_atomic(self.context):
            delivery.claim(self.context, self.conversation.pk)
        self.assertEqual(ExternalAgentDeliveryItem.objects.get().state, "suppressed")
        self.assertFalse(self.sender.called)

    def test_deleted_template_is_a_conflict_before_acceptance(self):
        skill, template = self.template()
        row = self.request()
        self.claim()
        skill.delete()
        body = self.result(row)
        body["outcome"]["messages"][0]["content"] = self.formatted(template)
        response = self.callback(row, body)
        self.assertEqual(response.status_code, 409, response.content)
        self.assertEqual(response.json()["error"]["code"], "template_revision_changed")
        self.assertFalse(Message.objects.filter(author_type="AI").exists())

    def test_web_formatted_publishes_the_native_safe_snapshot(self):
        self.template_skill, template = self.template()
        self.messaging.provider = "WEB"
        self.messaging.save(update_fields=["provider"])
        with patch("chatballs.ai.external_agents.auth.consent_current", return_value=True), \
             patch("chatballs.ai.external_agents.readiness.consent_current", return_value=True):
            row = self.request()
            self.claim()
            body = self.result(row)
            body["outcome"]["messages"][0]["content"] = self.formatted(template)
            response = self.callback(row, body)
        self.assertEqual(response.status_code, 200, response.content)
        message = Message.objects.get(author_type="AI")
        self.assertEqual(message.delivery_representation, "html")
        self.assertEqual(message.presentation["sandbox"], "")
        self.assertEqual(message.presentation["isolation"], "sandboxed-iframe")
        self.assertEqual(ExternalAgentDeliveryItem.objects.get().state, "transport_accepted")
        self.assertFalse(self.sender.called)
