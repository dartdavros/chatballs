"""Вход через сервис по OAuth на независимом тестовом адаптере (SPEC-0037 R-7, R-30)."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase, override_settings
from django.utils import timezone

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import EmployeeRole, HumanUser, Organization, OrganizationMembership
from chatballs.integrations.adapters.contracts import ResultState
from chatballs.integrations.adapters.registry import reset_registry
from chatballs.integrations.models import (
    Integration,
    IntegrationStatus,
    OAuthStateStatus,
    ServiceConnectionSettings,
    ServiceOAuthState,
)
from chatballs.integrations.service_connections import binding, oauth
from chatballs.integrations.service_connections.transport_testing import FakeService, json_response
from chatballs.testing import TenantAPIClient, tenant_context_for

URL = "/api/v1/integrations/"
CALLBACK = "/api/v1/service-oauth/callback/"
ADAPTERS = ["chatballs.integrations.adapters.bitrix24", "chatballs.integrations.adapters.probe_testing"]
CLIENTS = {"probe": {"client_id": "chatballs-app", "client_secret": "app-secret"}}


@override_settings(CHATBALLS_SERVICE_ADAPTERS=ADAPTERS, CHATBALLS_SERVICE_OAUTH_CLIENTS=CLIENTS)
class ServiceOAuthTests(TestCase):
    def setUp(self) -> None:
        reset_registry()
        self.addCleanup(reset_registry)
        self.owner = bootstrap_owner(email="oauth-owner@example.com", password="temporary-password").owner
        self.organization = Organization.objects.get(slug="demo")
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)
        self.service = FakeService(self, {
            "/token": json_response({"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 3600}),
            "/account": json_response({"id": "acc"}),
        })

    def _start(self, **extra) -> tuple[dict, str]:
        response = self.client.post(
            f"{URL}services/oauth/start/",
            {"adapter": "probe", "authMethod": "oauth", "name": "Probe", "values": {"base_url": "https://api.probe.test/"}, **extra},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        token = parse_qs(urlsplit(body["authorizeUrl"]).query)["state"][0]
        return body, token

    def _callback(self, token: str, client: TenantAPIClient | None = None, **params):
        return (client or self.client).get(CALLBACK, {"state": token, **params})

    def test_start_gives_a_pkce_link_and_keeps_only_the_state_hash(self) -> None:
        body, token = self._start()

        query = parse_qs(urlsplit(body["authorizeUrl"]).query)
        self.assertEqual(query["client_id"], ["chatballs-app"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["scope"], ["orders"])
        state = ServiceOAuthState.objects.get()
        self.assertNotEqual(state.state_hash, token)
        self.assertEqual((state.user, state.organization, state.status), (self.owner, self.organization, OAuthStateStatus.PENDING))
        self.assertNotIn("app-secret", json.dumps(body))

    def test_callback_creates_the_connection_once(self) -> None:
        body, token = self._start()

        first = self._callback(token, code="code-1")
        second = self._callback(token, code="code-1")

        self.assertEqual(first.status_code, 302)
        self.assertEqual(first["Location"], "/settings/integrations/services?serviceOauth=done")
        self.assertEqual(second.status_code, 302)
        state = self.client.get(f"{URL}services/oauth/{body['state']['id']}/").json()["state"]
        self.assertEqual(state["status"], "completed")
        connection = Integration.objects.get(id=state["connectionId"])
        self.assertEqual(connection.status, IntegrationStatus.OK)
        self.assertEqual(Integration.objects.filter(provider="ADAPTER").count(), 1)
        row = ServiceConnectionSettings.objects.get()
        self.assertEqual(json.loads(row.credentials)["access_token"], "at-1")
        token_form = parse_qs(self.service.requests[0].body.decode())
        self.assertEqual((token_form["grant_type"], token_form["code"]), (["authorization_code"], ["code-1"]))
        self.assertTrue(token_form["code_verifier"][0])

    def test_state_is_bound_to_the_user_who_started(self) -> None:
        _body, token = self._start()
        colleague = HumanUser.objects.create_user(email="oauth-colleague@example.com")
        OrganizationMembership.objects.create(organization=self.organization, user=colleague, role=EmployeeRole.ADMIN, position_title="Admin")
        other = TenantAPIClient()
        other.force_authenticate(colleague)

        self._callback(token, client=other, code="code-1")

        self.assertEqual(ServiceOAuthState.objects.get().status, OAuthStateStatus.PENDING)
        self.assertFalse(Integration.objects.filter(provider="ADAPTER").exists())
        self.assertEqual(self.service.requests, [])

    def test_forged_and_expired_states_are_refused(self) -> None:
        _body, token = self._start()
        ServiceOAuthState.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        self._callback(f"{self.organization.public_id}.forged", code="code-1")
        self._callback(token, code="code-1")

        state = ServiceOAuthState.objects.get()
        self.assertEqual((state.status, state.error_code), (OAuthStateStatus.FAILED, "oauth_expired"))
        self.assertFalse(Integration.objects.filter(provider="ADAPTER").exists())

    def test_denied_access_does_not_create_a_connection(self) -> None:
        body, token = self._start()

        self._callback(token, error="access_denied")

        state = self.client.get(f"{URL}services/oauth/{body['state']['id']}/").json()["state"]
        self.assertEqual(state["status"], "denied")
        self.assertEqual(state["error"]["title"], "Доступ не предоставлен.")
        self.assertFalse(Integration.objects.filter(provider="ADAPTER").exists())

    def _connected(self) -> Integration:
        _body, token = self._start()
        self._callback(token, code="code-1")
        self.service.requests.clear()
        ServiceConnectionSettings.objects.update(credentials_expires_at=timezone.now() - timedelta(seconds=5))
        return Integration.objects.get(provider="ADAPTER")

    def test_expired_token_is_refreshed_before_the_operation(self) -> None:
        integration = self._connected()
        self.service.routes["/token"] = json_response({"access_token": "at-2", "expires_in": 3600})

        result = binding.execute(tenant=tenant_context_for(self.owner), integration=integration, operation_key="account.get", arguments={})

        self.assertEqual(result.state, ResultState.COMPLETED)
        self.assertEqual(parse_qs(self.service.requests[0].body.decode())["refresh_token"], ["rt-1"])
        self.assertEqual(self.service.requests[1].headers["Authorization"], "Bearer at-2")
        row = ServiceConnectionSettings.objects.get()
        self.assertEqual((json.loads(row.credentials)["refresh_token"], row.refresh_claim), ("rt-1", None))

    def test_concurrent_refresh_waits_for_the_one_who_refreshes(self) -> None:
        integration = self._connected()
        row = ServiceConnectionSettings.objects.get()
        ServiceConnectionSettings.objects.filter(pk=row.pk).update(
            refresh_claim="00000000-0000-0000-0000-000000000001", refresh_claim_until=timezone.now() + timedelta(seconds=30)
        )

        def other_worker_finishes(_seconds) -> None:
            ServiceConnectionSettings.objects.filter(pk=row.pk).update(
                credentials=binding.dump_credentials({"access_token": "at-other", "refresh_token": "rt-2"}),
                credentials_expires_at=timezone.now() + timedelta(hours=1),
                refresh_claim=None, refresh_claim_until=None,
            )

        with mock.patch.object(oauth.time, "sleep", other_worker_finishes):
            result = binding.execute(tenant=tenant_context_for(self.owner), integration=integration, operation_key="account.get", arguments={})

        self.assertEqual(result.state, ResultState.COMPLETED)
        self.assertEqual([request.url.rsplit("/", 1)[-1] for request in self.service.requests], ["account"])
        self.assertEqual(self.service.requests[0].headers["Authorization"], "Bearer at-other")

    def test_revoked_refresh_marks_access_lost(self) -> None:
        integration = self._connected()
        self.service.routes["/token"] = json_response({"error": "invalid_grant"}, status=400)

        result = binding.execute(tenant=tenant_context_for(self.owner), integration=integration, operation_key="account.get", arguments={})

        self.assertEqual((result.state, result.error_code), (ResultState.FAILED, "access_revoked"))
        integration.refresh_from_db()
        self.assertEqual((integration.status, integration.last_error_code), (IntegrationStatus.ERROR, "access_revoked"))
        payload = self.client.get(f"{URL}services/{integration.id}/").json()["connection"]
        self.assertEqual(payload["status"], "lost")
        self.assertIsNone(ServiceConnectionSettings.objects.get().refresh_claim)

    def test_stale_snapshot_uses_the_token_already_refreshed_by_another_worker(self) -> None:
        integration = self._connected()
        row = ServiceConnectionSettings.objects.get()
        ServiceConnectionSettings.objects.filter(pk=row.pk).update(
            credentials=binding.dump_credentials({"access_token": "at-newer", "refresh_token": "rt-newer"}),
            credentials_expires_at=timezone.now() + timedelta(hours=1),
        )
        credentials = oauth.fresh_credentials(tenant=tenant_context_for(self.owner), integration=integration, row=row,
                                              method=binding.resolve(integration)[2])
        self.assertEqual(credentials["access_token"], "at-newer")
        self.assertEqual(self.service.requests, [])

    def test_waiter_does_not_use_expired_credentials_after_failed_refresh(self) -> None:
        self._connected()
        row = ServiceConnectionSettings.objects.get()
        with mock.patch.object(oauth.time, "sleep", lambda _: None), self.assertRaises(oauth.OAuthFailed):
            oauth._wait_for_refresh(tenant=tenant_context_for(self.owner), row=row)

    def test_late_refresh_failure_does_not_revoke_replaced_access(self) -> None:
        import uuid

        integration = self._connected()
        row = ServiceConnectionSettings.objects.get()
        oauth._release(tenant_context_for(self.owner), row, uuid.uuid4(), lost="access_revoked", integration=integration)
        integration.refresh_from_db()
        self.assertEqual(integration.status, IntegrationStatus.OK)
