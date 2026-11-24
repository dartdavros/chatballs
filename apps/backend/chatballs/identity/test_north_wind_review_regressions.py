from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings

from chatballs.conversations.comment_models import ConversationComment
from chatballs.conversations.comment_services import create_comment
from chatballs.conversations.models import Conversation
from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxEvent
from chatballs.identity.demo_seed.north_wind.appointments import MOSCOW
from chatballs.identity.demo_seed.north_wind.seed_entries import _shift_timing
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.setup import SetupInput, complete_setup
from chatballs.identity.test_seed_demo import _MEDIA_ROOT, OWNER
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient


class NorthWindShiftTests(SimpleTestCase):
    def test_conversation_timeline_stays_in_moscow_date_after_midnight(self):
        count = 10
        for moment in (datetime(2026, 11, 24, 0, 0, 1, tzinfo=MOSCOW), datetime(2026, 11, 24, 10, 0, tzinfo=MOSCOW)):
            with self.subTest(moment=moment):
                cadence, starts = _shift_timing(moment, count)
                self.assertEqual(len(starts), count)
                self.assertTrue(all(start.date() == moment.date() for start in starts))
                self.assertLess(starts[-1], starts[0])
                self.assertLessEqual(cadence, timedelta(seconds=10))


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class NorthWindOfflineResetTests(TestCase):
    @patch.dict("os.environ", {"CHATBALLS_LOCAL_NORTH_WIND": "0"})
    def test_offline_reinstall_removes_new_and_preexisting_demo_comments(self):
        setup = complete_setup(SetupInput(**OWNER))
        client = TenantAPIClient()
        client.login(username=OWNER["email"], password=OWNER["password"])
        path = "/api/v1/company/demo/"
        self.assertEqual(client.post(path).status_code, 202)
        dispatch(OutboxEvent.objects.get(event_type="demo.install_requested"))
        initial = client.get(path).json()
        self.assertEqual(initial["status"], "INSTALLED", initial["error"])

        member = OrganizationMembership.objects.get(organization=setup.organization, user=setup.owner)
        context = TenantContext.for_membership(member)
        with tenant_atomic(context):
            dialogue = Conversation.objects.get(external_chat_id__endswith=":team")
            comment, _ = create_comment(
                context=context, conversation_id=dialogue.pk, audience="INTERNAL", text="New comment", operation_id=uuid4(),
            )
            registered = dialogue.organization.demo_dataset.records.filter(
                content_type__app_label="conversations", content_type__model="conversationcomment",
                object_id=str(comment.pk),
            )
            self.assertTrue(registered.exists())
            registered.delete()  # Simulate a comment written before this fix.

        queued = client.post(path + "reinstall/", {
            "generation": initial["generation"], "previousRequestId": None, "requestId": str(uuid4()),
        }, format="json")
        self.assertEqual(queued.status_code, 202, queued.data)
        dispatch(OutboxEvent.objects.get(event_type="demo.reinstall_requested"))
        updated = client.get(path).json()
        self.assertEqual(updated["reinstall"], {"status": "SUCCEEDED", "errorCode": ""})
        self.assertNotEqual(updated["generation"], initial["generation"])
        self.assertFalse(ConversationComment.objects.filter(pk=comment.pk).exists())
