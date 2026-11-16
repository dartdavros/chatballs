"""Scoped reverse pagination and logical turn order through the real GET API."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from chatballs.ai.external_agents.context_testing import ContextData
from chatballs.ai.external_agents.history_payloads import cursor
from chatballs.conversations.models import Message


class ContextHistoryTests(ContextData, TestCase):
    def get_page(self, row, query=None, *, conversation_id=None):
        return self.client.get(
            f"/api/v1/external-agent/connections/{self.connection.pk}/conversations/{conversation_id or self.conversation.pk}/history/",
            query if query is not None else {"authorizationId": str(row.authorization_id), "snapshotCursor": cursor(row)},
            HTTP_AUTHORIZATION="Bearer " + self.created["incomingKey"])

    def test_inline_and_reverse_pages_cover_every_public_id_once_with_deletions(self):
        prior = [Message.objects.create(conversation=self.conversation, author_type="OPERATOR", text=str(i))
                 for i in range(27)]
        row = self.request()
        future = self.request("Future customer")
        Message.objects.create(conversation=self.conversation, author_type="SYSTEM", text="PRIVATE")
        self.claim()
        window = self.frozen(row)["context"]["history"]
        prior[2].delete()
        collected = window["messages"]
        continuation = window["nextCursor"]
        while continuation:
            response = self.get_page(row, {"authorizationId": str(row.authorization_id),
                "snapshotCursor": window["snapshotCursor"], "pageCursor": continuation, "pageSize": 3})
            self.assertEqual(response.status_code, 200, response.content)
            data = response.json()
            collected = data["items"] + collected
            continuation = data["nextCursor"]
        identifiers = [item["id"] for item in collected]
        self.assertEqual(identifiers, [str(message.pk) for i, message in enumerate(prior) if i != 2])
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertNotIn(str(row.trigger_id), identifiers)
        self.assertNotIn(str(future.trigger_id), identifiers)
        self.assertEqual(self.get_page(row).headers["Cache-Control"], "no-store")

    def test_query_limits_binding_tampering_deadline_and_feature_are_enforced(self):
        row = self.request()
        self.claim()
        query = {"authorizationId": str(row.authorization_id), "snapshotCursor": cursor(row)}
        for update in ({"pageSize": 0}, {"pageSize": 201}, {"pageSize": "1.0"},
                       {"snapshotCursor": "x" * 4097}, {"pageCursor": "x" * 4097},
                       {"snapshotCursor": cursor(row, 0)}, {"pageCursor": cursor(row, -1)},
                       {"pageCursor": cursor(row, 1000)}, {"snapshotCursor": "bad"}):
            with self.subTest(update=update):
                self.assertEqual(self.get_page(row, {**query, **update}).status_code, 400)
        self.assertEqual(self.get_page(row, {}).status_code, 400)
        self.assertEqual(self.get_page(row, {"authorizationId": str(row.authorization_id)}).status_code, 400)
        self.assertEqual(self.get_page(row, {"snapshotCursor": cursor(row)}).status_code, 400)
        self.assertEqual(self.get_page(row, conversation_id=self.conversation.pk + 9999).status_code, 404)
        with self.subTest(deadline=True):
            from unittest.mock import patch

            with patch("chatballs.ai.external_agents.history.timezone.now", return_value=row.deadline_at):
                self.assertEqual(self.get_page(row).status_code, 409)
        self.client.patch(self.url, {"enabled": False}, format="json")
        self.assertEqual(self.get_page(row).status_code, 403)

    def test_default_50_max_200_and_message_count_budget(self):
        for i in range(205):
            Message.objects.create(conversation=self.conversation, author_type="OPERATOR", text=str(i))
        row = self.request()
        self.claim()
        self.assertEqual(len(self.get_page(row).json()["items"]), 50)
        response = self.get_page(row, {"authorizationId": str(row.authorization_id),
                                      "snapshotCursor": cursor(row), "pageSize": 200})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.json()["items"]), 200)

    def test_previous_answer_is_ordered_after_its_trigger_despite_physical_timestamps(self):
        first = self.request("first")
        second = self.request("second")
        self.claim()
        self.accept(first, self.result(first))
        answer = Message.objects.get(author_type="AI")
        Message.objects.filter(pk=answer.pk).update(created_at=timezone.now() - timedelta(days=2))
        self.deliver()
        self.claim()
        messages = self.frozen(second)["context"]["history"]["messages"]
        self.assertEqual([item["content"]["text"] for item in messages], ["first", "Answer"])
        self.assertEqual([item["author"] for item in messages], ["customer", "agent"])

    def test_contact_public_text_and_language_are_preserved_without_vcard(self):
        prior = Message.objects.create(conversation=self.conversation, author_type="OPERATOR",
                                       kind="contact", text="Stored public contact")
        self.agent.answer_language = "en"
        self.agent.save(update_fields=["answer_language"])
        row = self.request("Contact supplied by customer", kind="contact")
        self.claim()
        data = self.frozen(row)
        self.assertEqual(data["trigger"]["type"], "contact")
        self.assertEqual(data["trigger"]["text"], row.trigger.text)
        self.assertEqual(data["trigger"]["attachments"], [])
        self.assertEqual(data["context"]["history"]["messages"][0]["id"], str(prior.pk))
        self.assertEqual(data["context"]["history"]["messages"][0]["author"], "employee")
        self.assertEqual(data["context"]["customer"]["fields"], {})
        self.assertEqual(data["context"]["language"]["requested"], "en")

    def test_result_contact_and_schema_patches_are_rejected_at_http_boundary(self):
        row = self.request()
        self.claim()
        for key in ("customer", "customFields", "contactPatch", "definitions"):
            result = self.result(row)
            result[key] = {"name": "PRIVATE"}
            self.assertEqual(self.callback(row, result).status_code, 400)
        self.assertFalse(Message.objects.filter(author_type="AI").exists())
