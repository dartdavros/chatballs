from unittest.mock import patch
from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from chatballs.conversations.domain_event_test_base import DomainEventTestBase
from chatballs.conversations.domain_events import record_fact
from chatballs.conversations.models import Conversation, ConversationRead, Message, MessageKind
from chatballs.events.handlers import dispatch
from chatballs.events.models import OutboxEvent
from chatballs.identity.audit import record_audit_event
from chatballs.identity.audit_models import AuditEvent
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus, DemoRecord
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.setup import SetupInput, complete_setup
from chatballs.identity.test_seed_demo import _MEDIA_ROOT, OWNER
from chatballs.notifications.models import (
    Notification,
    NotificationAudience,
    NotificationRead,
    NotificationType,
)
from chatballs.notifications.services import notify
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient
from chatballs.webchat.models import WebChatWidget, WebSession
from chatballs.webchat.sessions import hash_session_token, issue_session


class DemoReinstallationTests(DomainEventTestBase):
    @patch.dict("os.environ", {"CHATBALLS_LOCAL_NORTH_WIND": "1"})
    def test_worker_preserves_working_dialog_and_deduplicates_requests(self):
        context = TenantContext.for_resource(self.organization)
        with tenant_atomic(context):
            membership = OrganizationMembership.objects.get(
                organization=self.organization, user=self.user,
            )
            membership.role = "ADMIN"
            membership.save(update_fields=["role"])
            working = Conversation.objects.create(
                organization=self.organization,
                channel=self.conversation.channel,
                connection=self.conversation.connection,
                contact=self.conversation.contact,
                previous_conversation=self.conversation,
                external_chat_id=str(uuid4()),
            )
            dataset = DemoDataset.objects.create(
                organization=self.organization, status=DemoDatasetStatus.INSTALLED,
                generation=uuid4(), records_count=1,
            )
            DemoRecord.objects.create(
                organization=self.organization, dataset=dataset,
                content_type=ContentType.objects.get_for_model(Conversation),
                object_id=str(self.conversation.pk), sequence=1,
            )

        client = TenantAPIClient()
        client.force_authenticate(self.user)
        request_data = {
            "requestId": str(uuid4()), "generation": str(dataset.generation),
            "previousRequestId": None,
        }
        url = "/api/v1/company/demo/reinstall/"
        for _ in range(2):
            queued = client.post(url, request_data, format="json")
            self.assertEqual(queued.status_code, 202, queued.data)
            self.assertEqual(queued.json()["reinstall"]["status"], "RUNNING")
        different = client.post(url, {**request_data, "requestId": str(uuid4())}, format="json")
        self.assertEqual(different.status_code, 409)

        event = OutboxEvent.objects.get(event_type="demo.reinstall_requested")
        dispatch(event)
        dispatch(event)
        state = client.get("/api/v1/company/demo/").json()
        self.assertEqual(state["status"], "INSTALLED")
        self.assertEqual(state["generation"], str(dataset.generation))
        self.assertEqual(state["reinstall"], {"status": "FAILED", "errorCode": "WORKING_CONVERSATION"})
        working.refresh_from_db()
        self.assertEqual(working.previous_conversation_id, self.conversation.pk)
        self.assertEqual(client.post(url, request_data, format="json").status_code, 202)
        self.assertEqual(OutboxEvent.objects.filter(event_type="demo.reinstall_requested").count(), 1)


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class NorthWindReinstallationTests(TestCase):
    @patch("chatballs.identity.demo_seed.north_wind.seed_executor.check_capabilities", return_value={"versions": ["1"]})
    @patch("chatballs.identity.demo_seed.north_wind.seed_tools.verify_mock_service")
    @patch("chatballs.identity.demo_seed.north_wind.delivery_scenarios.verify_delivery_service")
    def test_legacy_set_is_replaced_and_mock_store_is_reset(self, verify_delivery_service, verify_mock_service, check_executor):
        setup = complete_setup(SetupInput(**OWNER))
        client = TenantAPIClient()
        client.force_authenticate(setup.owner)
        self.assertEqual(client.post("/api/v1/company/demo/").status_code, 202)
        dispatch(OutboxEvent.objects.get(event_type="demo.install_requested"))
        admin = HumanUser.objects.get(email="e.kuznetsova@severny-veter.test")
        login = record_audit_event(action="identity.login_succeeded", actor=admin)
        context = TenantContext.for_resource(setup.organization)
        with tenant_atomic(context):
            organization_audit = record_audit_event(
                action="administration.organization_updated", organization=setup.organization,
                actor=admin, object_type="Organization", object_id=str(setup.organization.public_id),
                payload={"operationModeVersion": setup.organization.operation_mode_version},
            )
            old = DemoDataset.objects.get(organization=setup.organization)
            legacy = Conversation.objects.get(external_chat_id__endswith=":pickup")
            legacy.external_chat_id = "legacy-demo-chat"
            legacy.save(update_fields=["external_chat_id"])
            state = old.shop_state
            state["balances"]["andrey"] = 750
            state["stock"]["alpine:L:center"] = 2
            old.shop_state = state
            old.save(update_fields=["shop_state"])
            conversation = Conversation.objects.get(external_chat_id__endswith=":delivery")
            assignment = record_fact(conversation, "ASSIGNED", actor_kind="HUMAN", initiated_by_id=admin.pk)
            assignment_notice = Message.objects.create(conversation=conversation, author_type="SYSTEM", text="Assignment")
            read = ConversationRead.objects.create(
                organization=setup.organization, conversation=conversation, user=admin,
            )
            assignee_notice = notify(
                context=context, type=NotificationType.DIALOG_ASSIGNED, audience=NotificationAudience.USER,
                recipient_user=admin, title="Assigned", source_type="Conversation", source_id=conversation.pk,
                target_id=conversation.pk,
            )
            reminder = notify(
                context=context, type=NotificationType.DIALOG_WAITING_LONG, audience=NotificationAudience.OPERATORS,
                audience_group=conversation.group, title="Waiting for an operator", source_type="Conversation",
                source_id=conversation.pk, target_id=conversation.pk, dedup_key=f"waiting:{conversation.pk}:remind",
            )
            direct_reminder = notify(
                context=context, type=NotificationType.DIALOG_WAITING_LONG, audience=NotificationAudience.USER,
                recipient_user=admin, title="Waiting for an operator", source_type="Conversation",
                source_id=conversation.pk, target_id=conversation.pk,
                dedup_key=f"waiting:{conversation.pk}:management:user:{admin.pk}",
            )
            read_notice = NotificationRead.objects.create(
                organization=setup.organization, notification=direct_reminder, user=admin,
            )
            integration_audit = record_audit_event(
                action="integrations.integration_tested", organization=setup.organization,
                actor=admin, object_type="Integration", object_id=str(conversation.connection_id),
            )

        with patch.dict("os.environ", {"CHATBALLS_LOCAL_NORTH_WIND": "1"}):
            client.force_authenticate(admin)
            self.assertEqual(client.get("/api/v1/notifications/preferences/BROWSER/").status_code, 200)
            request = client.post("/api/v1/company/demo/reinstall/", {
                "requestId": str(uuid4()), "generation": str(old.generation),
                "previousRequestId": None,
            }, format="json")
            self.assertEqual(request.status_code, 202, request.data)
            dispatch(OutboxEvent.objects.get(event_type="demo.reinstall_requested"))

        client.force_authenticate(setup.owner)
        status = client.get("/api/v1/company/demo/").json()
        self.assertEqual(status["reinstall"], {"status": "SUCCEEDED", "errorCode": ""})
        self.assertTrue(status["northWind"])
        verify_mock_service.assert_called_once()
        verify_delivery_service.assert_called_once()
        check_executor.assert_called_once()
        self.assertNotEqual(status["generation"], str(old.generation))
        login.refresh_from_db()
        self.assertIsNone(login.actor_id)
        with tenant_atomic(context):
            saved_audit = AuditEvent.objects.get(pk=organization_audit.pk)
            self.assertIsNone(saved_audit.actor_id)
            self.assertEqual(saved_audit.payload, organization_audit.payload)
            self.assertIsNone(AuditEvent.objects.get(pk=integration_audit.pk).actor_id)
            self.assertFalse(type(assignment).objects.filter(pk=assignment.pk).exists())
            self.assertFalse(Message.objects.filter(pk=assignment_notice.pk).exists())
            self.assertFalse(ConversationRead.objects.filter(pk=read.pk).exists())
            self.assertFalse(NotificationRead.objects.filter(pk=read_notice.pk).exists())
            audit = AuditEvent.objects.get(action="demo.reinstalled")
            self.assertFalse(Notification.objects.filter(pk__in=(assignee_notice.pk, reminder.pk, direct_reminder.pk)).exists())
            self.assertEqual(audit.payload["actorUserId"], admin.pk)
            new = DemoDataset.objects.get(pk=old.pk)
            self.assertEqual(new.shop_state["balances"]["andrey"], 1500)
            self.assertEqual(new.shop_state["stock"]["alpine:L:center"], 3)
            entries = Conversation.objects.filter(
                organization=setup.organization, external_chat_id__startswith=f"north-wind:{new.generation}:",
            )
            self.assertEqual(entries.count(), 10)
            self.assertEqual(Conversation.objects.filter(organization=setup.organization).count(), 10)
            self.assertFalse(Conversation.objects.filter(pk=legacy.pk).exists())
            exchange = entries.get(external_chat_id__endswith=":exchange")
            self.assertEqual(new.shop_state["supportDialogs"]["exchange"]["conversationId"], exchange.pk)
            self.assertEqual(new.shop_state["supportDialogs"]["exchange"]["orderNumber"], 2042)
            team = entries.get(external_chat_id__endswith=":team")
            self.assertEqual(team.comments.count(), 2)
            self.assertEqual(team.messages.get(kind=MessageKind.FILE).attachment_content_type, "image/jpeg")
            self.assertEqual(team.lifecycle, "OPEN")
            self.assertEqual(team.participants.active().count(), 2)
            formatted = entries.get(external_chat_id__endswith=":formatted")
            self.assertEqual(formatted.connection.channel.code, "site-support")
            delivery = entries.get(external_chat_id__endswith=":delivery")
            self.assertEqual((delivery.control_mode, delivery.expected_responder), ("HUMAN", "OPERATOR"))
            self.assertEqual(delivery.assigned_operator.email, "i.saveliev@severny-veter.test")
            self.assertEqual(delivery.priority, "HIGH")
            widget = WebChatWidget.objects.get(public_key=new.shop_state["storefront"]["widgetKey"])
            self.assertEqual(WebChatWidget.objects.filter(organization=setup.organization).count(), 2)
            self.assertEqual(new.shop_state["pickupSite"]["widgetKey"], widget.public_key)
            self.assertEqual(new.shop_state["loyaltySite"]["widgetKey"], widget.public_key)
            support_key = new.shop_state["supportDialogs"]["exchange"]["widgetKey"]
            self.assertNotEqual(support_key, widget.public_key)
            self.assertEqual(new.shop_state["supportDialogs"]["formatted-external"]["widgetKey"], support_key)
            issued = issue_session(context=context, widget=widget)
            self.assertIsNotNone(issued)
            session = WebSession.objects.get(widget=widget, token_hash=hash_session_token(issued["token"]))
            self.assertTrue(new.records.filter(
                content_type=ContentType.objects.get_for_model(WebSession), object_id=str(session.pk),
            ).exists())
        with patch.dict("os.environ", {"CHATBALLS_LOCAL_NORTH_WIND": "1"}):
            self._verify_executor_scope(context)
            self._verify_support_photo(client, setup.organization, new, exchange)
            self._verify_customer_entry(context, new)

    def _verify_executor_scope(self, context):
        from chatballs.identity.demo_seed.north_wind.executor_scope import uses_external_execution

        with tenant_atomic(context):
            executor = Conversation.objects.get(external_chat_id__endswith=":formatted-external")
            support = Conversation.objects.get(external_chat_id__endswith=":exchange")
            self.assertEqual(executor.channel_id, support.channel_id)
            agent = executor.channel.ai_agent
            self.assertTrue(uses_external_execution(agent, conversation=executor))
            self.assertFalse(uses_external_execution(agent, conversation=support))

    def _verify_customer_entry(self, context, dataset):
        from urllib.parse import parse_qs, urlsplit

        from chatballs.identity.demo_seed.north_wind.prepared_widget import prepared_chat_path
        from chatballs.webchat.consent import current_version

        fitting = dataset.shop_state["supportDialogs"]["fitting"]
        ticket = parse_qs(urlsplit(prepared_chat_path(dataset, "fitting")).fragment)["entry"][0]
        customer = TenantAPIClient()
        url = "/api/v1/webchat/session/"
        with tenant_atomic(context):
            widget = WebChatWidget.objects.get(public_key=fitting["widgetKey"])
            payload = {"widgetKey": widget.public_key, "demoEntry": ticket,
                       "hostOrigin": dataset.shop_state["storefront"]["origin"]}
            self.assertEqual(customer.post(url, payload, format="json").status_code, 400)
            payload["consentVersion"] = current_version(widget)
            invalid = customer.post(url, {**payload, "demoEntry": ticket + "tampered"}, format="json")
            self.assertEqual(invalid.status_code, 404)
            result = customer.post(url, payload, format="json")
            self.assertEqual(result.status_code, 201, result.data)
            session = WebSession.objects.get(token_hash=hash_session_token(result.data["token"]))
            self.assertEqual(session.identity_id, fitting["identityId"])
            self.assertTrue(session.consent_accepted_at)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {result.data['token']}",
                   "HTTP_ORIGIN": dataset.shop_state["storefront"]["origin"]}
        for text in ("Хочу записаться на примерку", "Alpine Pro и Ridge Motion"):
            sent = customer.post("/api/v1/webchat/messages/", {"text": text}, format="json", **headers)
            self.assertEqual(sent.status_code, 201, sent.data)
        with tenant_atomic(context):
            dialogue = Conversation.objects.get(pk=fitting["conversationId"])
            self.assertEqual(dialogue.control_mode, "AI")
            self.assertEqual(dialogue.domain_events.filter(event_type="QUEUE_EXITED", actor_kind="SYSTEM").count(), 1)
            self.assertEqual(dialogue.messages.filter(ai_turn_state="PENDING").count(), 2)

    def _verify_support_photo(self, client, organization, dataset, exchange):
        from chatballs.conversations.comment_services import create_comment
        from chatballs.conversations.models import Message
        from chatballs.identity.models import OrganizationMembership

        url = f"/api/v1/organizations/{organization.public_id}/company/demo/shop/{dataset.generation}/support-photo/"
        options = {"format": "json", "HTTP_IDEMPOTENCY_KEY": "demo-zipper-photo"}
        first = client.post(url, {"dialog": "exchange"}, **options)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(client.post(url, {"dialog": "exchange"}, **options).json(), first.json())
        with tenant_atomic(organization.pk):
            photo = Message.objects.get(pk=first.json()["messageId"])
            self.assertEqual(photo.conversation_id, exchange.pk)
            self.assertTrue(photo.attachment.storage.exists(photo.attachment.name))
            owner = OrganizationMembership.objects.get(organization=organization, role="OWNER")
            comment, _ = create_comment(
                context=TenantContext.for_membership(owner), conversation_id=exchange.pk,
                audience="INTERNAL", text="Confirmed the defect from the attached image", operation_id=uuid4(),
            )
            for record in (photo, comment):
                self.assertTrue(dataset.records.filter(
                    content_type=ContentType.objects.get_for_model(record), object_id=str(record.pk),
                ).exists())
