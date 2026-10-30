"""Сервисные подключения под ролью backend-app: RLS и проверка связей (SPEC-0037 R-2)."""

from __future__ import annotations

import io

from django.db import IntegrityError, InternalError, ProgrammingError, connection, transaction
from django.test import TransactionTestCase

from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import EmployeeRole, HumanUser, Organization, OrganizationMembership
from chatballs.integrations.adapters.files import store_service_file
from chatballs.integrations.models import Integration, ServiceConnectionSettings, ServiceFile
from chatballs.integrations.service_connections.binding import _file_opener
from chatballs.integrations.service_connections.transport_testing import FakeService, json_response
from chatballs.tenancy.database import tenant_atomic
from chatballs.testing import TenantAPIClient, tenant_context_for

WEBHOOK = "https://nord.bitrix24.ru/rest/1/RlsSecretKey123/"


class ServiceConnectionRuntimeRoleTests(TransactionTestCase):
    def setUp(self) -> None:
        FakeService(self, {"/scope.json": json_response({"result": ["crm", "user"]})})
        self.owner = bootstrap_owner(email="rls-service@example.com", password="temporary-password").owner
        self.organization = Organization.objects.get(slug="demo")
        self.other = Organization.objects.create(name="Other", slug="rls-service-other")
        self.other_owner = HumanUser.objects.create_user(email="rls-service-other@example.com")
        OrganizationMembership.objects.create(
            organization=self.other, user=self.other_owner, role=EmployeeRole.OWNER, position_title="Owner"
        )

    def _as_app_role(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE chatballs_runtime_app")
        try:
            return request()
        finally:
            with connection.cursor() as cursor:
                cursor.execute("RESET ROLE")

    def _client(self, user: HumanUser) -> TenantAPIClient:
        client = TenantAPIClient()
        client.force_authenticate(user)
        return client

    def _url(self, organization: Organization, suffix: str = "") -> str:
        return f"/api/v1/organizations/{organization.public_id}/integrations/services/{suffix}"

    def test_connection_lives_only_in_its_organization(self) -> None:
        owner = self._client(self.owner)
        created = self._as_app_role(lambda: owner.post(
            self._url(self.organization),
            {"adapter": "bitrix24", "authMethod": "webhook", "name": "CRM", "values": {"url": WEBHOOK}},
            format="json",
        ))
        self.assertEqual(created.status_code, 201, created.content)
        connection_id = created.json()["connection"]["id"]
        stranger = self._client(self.other_owner)

        own = self._as_app_role(lambda: owner.get(self._url(self.organization)))
        foreign = self._as_app_role(lambda: stranger.get(self._url(self.other)))
        foreign_detail = self._as_app_role(lambda: stranger.get(self._url(self.other, f"{connection_id}/")))

        self.assertEqual([item["id"] for item in own.json()["items"]], [connection_id])
        self.assertEqual(foreign.json()["items"], [])
        self.assertEqual(foreign_detail.status_code, 404)

    def test_settings_cannot_point_to_a_foreign_connection(self) -> None:
        owner = self._client(self.owner)
        created = owner.post(
            self._url(self.organization),
            {"adapter": "bitrix24", "authMethod": "webhook", "name": "CRM", "values": {"url": WEBHOOK}},
            format="json",
        )
        row = ServiceConnectionSettings.objects.get(integration_id=created.json()["connection"]["id"])

        def move() -> None:
            with transaction.atomic(), tenant_atomic(self.organization.id):
                ServiceConnectionSettings.objects.filter(pk=row.pk).update(organization_id=self.other.id)

        with self.assertRaises((IntegrityError, InternalError, ProgrammingError)):
            self._as_app_role(move)

    def test_file_persistence_and_reads_establish_their_own_tenant_context(self) -> None:
        created = self._client(self.owner).post(
            self._url(self.organization),
            {"adapter": "bitrix24", "authMethod": "webhook", "name": "CRM", "values": {"url": WEBHOOK}},
            format="json",
        )
        integration = Integration.objects.get(pk=created.json()["connection"]["id"])
        context = tenant_context_for(self.owner, self.organization)
        stored = self._as_app_role(lambda: store_service_file(
            context=context, integration=integration, name="invoice.pdf", content_type="application/pdf",
            stream=io.BytesIO(b"pdf"), size=3,
        ))
        try:
            own = self._as_app_role(lambda: _file_opener(self.organization.id)(stored.file_id))
            self.assertEqual(own, ("invoice.pdf", "application/pdf", b"pdf"))
            with self.assertRaises(ServiceFile.DoesNotExist):
                self._as_app_role(lambda: _file_opener(self.other.id)(stored.file_id))
        finally:
            with tenant_atomic(context):
                ServiceFile.objects.get(public_id=stored.file_id).file.delete(save=False)
