from django.http import Http404
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from chatballs.ai.external_agents.auth import (
    authenticated,
    authorize_session,
    issue_authorization,
)
from chatballs.ai.external_agents.config_bindings import select_execution
from chatballs.ai.external_agents.config_models import ExternalAgentConnection
from chatballs.ai.external_agents.testing import ConfigurationCase
from chatballs.conversations.models import Contact, Conversation
from chatballs.identity.operation_modes import autonomous_allowed
from chatballs.tenancy.database import tenant_atomic


class AuthorityTests(ConfigurationCase):
    def setUp(self):
        super().setUp()
        self.created = self.connect()
        self.connection = ExternalAgentConnection.objects.get(pk=self.created["connection"]["id"])
        self.bind(self.connection.pk)
        select_execution(self.context, self.agent.pk, "external")
        contact = Contact.objects.create(organization=self.organization, name="Test contact")
        self.conversation = Conversation.objects.create(organization=self.organization, channel=self.channel, contact=contact)

    def issue(self):
        with tenant_atomic(self.context):
            return issue_authorization(self.context, self.connection, self.agent.pk, self.conversation.pk)

    def authorize(self, session, *, token=None, **overrides):
        with authenticated("Bearer " + (token or self.created["incomingKey"])) as (context, connection):
            return authorize_session(context, connection, **{
                "conversation_id": self.conversation.pk, "authorization_id": session.authorization_id,
                "operation": "history", **overrides,
            })

    def test_key_resolves_tenant_and_foreign_scope_is_404(self):
        session = self.issue()
        self.assertEqual(self.authorize(session).pk, session.pk)
        with self.assertRaises(Http404):
            self.authorize(session, conversation_id=self.conversation.pk + 10000)
        with self.assertRaises(AuthenticationFailed):
            self.authorize(session, token="wrong-key" * 8)
        with self.assertRaises(PermissionDenied):
            self.authorize(session, operation="proxy")
        with self.assertRaises(PermissionDenied):
            self.authorize(session, operation="messages")

    def test_rotation_revokes_old_key_and_old_authority_keeps_dedup_key(self):
        session = self.issue()
        before = self.connection.deduplication_key
        response = self.client.post(self.url + f"connections/{self.connection.pk}/key/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        rotated = response.json()["incomingKey"]
        with self.assertRaises(AuthenticationFailed):
            self.authorize(session)
        with self.assertRaises(PermissionDenied):
            self.authorize(session, token=rotated)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.deduplication_key, before)
        fresh = self.issue()
        self.assertNotEqual(session.authorization_id, fresh.authorization_id)
        self.assertEqual(self.authorize(fresh, token=rotated).pk, fresh.pk)

    def test_disable_reenable_and_mode_aba_never_revive_authority(self):
        for cycle in ("feature", "mode", "control", "binding", "unlink", "connection"):
            with self.subTest(cycle=cycle):
                session = self.issue()
                if cycle == "feature":
                    for enabled in (False, True):
                        self.client.patch(self.url, {"enabled": enabled}, format="json")
                elif cycle == "mode":
                    for mode in ("builtin", "external"):
                        select_execution(self.context, self.agent.pk, mode)
                elif cycle == "control":
                    for mode in ("HUMAN", "AI"):
                        self.conversation.control_mode = mode
                        self.conversation.save(update_fields=["control_mode"])
                elif cycle == "binding":
                    self.bind(self.connection.pk, externalAgentId="other-agent")
                    self.bind(self.connection.pk)
                elif cycle == "unlink":
                    response = self.client.delete(self.url + f"connections/{self.connection.pk}/bindings/{self.agent.pk}/")
                    self.assertEqual(response.status_code, 204)
                    self.assertEqual(self.client.get(self.url).json()["connections"][0]["bindings"], [])
                    self.bind(self.connection.pk)
                else:
                    for enabled in (False, True):
                        self.client.patch(self.url + f"connections/{self.connection.pk}/", {"enabled": enabled}, format="json")
                with self.assertRaises(PermissionDenied):
                    self.authorize(session)
                if cycle == "feature":
                    with self.assertRaises(PermissionDenied):
                        self.issue()
                    checked = self.client.post(self.url + f"connections/{self.connection.pk}/check/", {}, format="json")
                    self.assertEqual(checked.status_code, 200, checked.content)
                    self.bind(self.connection.pk)
                self.assertNotEqual(session.authorization_id, self.issue().authorization_id)

    def test_external_does_not_need_llm_and_never_falls_back(self):
        self.organization.refresh_from_db()
        self.agent.refresh_from_db()
        self.channel.ai_agent = self.agent
        self.assertTrue(autonomous_allowed(self.channel, organization=self.organization))
        self.client.patch(self.url, {"enabled": False}, format="json")
        self.organization.refresh_from_db()
        self.assertFalse(autonomous_allowed(self.channel, organization=self.organization))
        from django.core.exceptions import ValidationError

        from chatballs.ai.runtime import run_agent_turn
        with self.assertRaises(ValidationError):
            run_agent_turn(agent=self.agent, message="Test")
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.execution_mode, "external")

    def test_policy_changes_keep_session_identity_but_rotate_authority(self):
        session = self.issue()
        self.bind(self.connection.pk, standardFields=["name"])
        with self.assertRaises(PermissionDenied):
            self.authorize(session)
        refreshed = self.issue()
        self.assertEqual(session.public_id, refreshed.public_id)
        self.assertNotEqual(session.authorization_id, refreshed.authorization_id)
