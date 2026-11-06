"""API сервисных подключений на адаптере Битрикс24 (SPEC-0037 R-1, R-6, R-7, R-14)."""

from __future__ import annotations

import json

from django.db import connection
from django.test import TestCase

from chatballs.i18n import t
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import (
    AuditEvent,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    ServiceConnectionSettings,
)
from chatballs.integrations.service_connections.transport_testing import FakeService, json_response
from chatballs.testing import TenantAPIClient

URL = "/api/v1/integrations/"
WEBHOOK = "https://nord.bitrix24.ru/rest/1/s3cr3tWebhookKey42/"
SECRET = "s3cr3tWebhookKey42"


class ServiceConnectionApiTests(TestCase):
    def setUp(self) -> None:
        self.owner = bootstrap_owner(email="service-owner@example.com", password="temporary-password").owner
        self.organization = Organization.objects.get(slug="demo")
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)
        self.service = FakeService(self, {"/scope.json": json_response({"result": ["crm", "user", "task"]})})

    def _connect(self, name: str = "Битрикс24 · Продажи", url: str = WEBHOOK):
        return self.client.post(
            f"{URL}services/",
            {"adapter": "bitrix24", "authMethod": "webhook", "name": name, "values": {"url": url}},
            format="json",
        )

    def _connected(self, **kwargs) -> dict:
        response = self._connect(**kwargs)
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["connection"]

    def test_catalog_describes_installed_adapter_from_its_contract(self) -> None:
        response = self.client.get(f"{URL}service-adapters/")

        self.assertEqual(response.status_code, 200)
        (adapter,) = response.json()["items"]
        self.assertEqual((adapter["key"], adapter["title"]), ("bitrix24", "Битрикс24"))
        self.assertTrue(adapter["logo"]["light"].startswith("data:image/svg+xml;base64,"))
        (method,) = adapter["authMethods"]
        (field,) = method["fields"]
        self.assertEqual((field["name"], field["secret"], field["control"]), ("url", True, "url@1"))
        self.assertEqual(field["patternError"], t("services.bitrix24.webhook_url_invalid"))
        (preset,) = adapter["presets"]
        self.assertEqual(preset["title"], "Создать лид из диалога")
        self.assertEqual([step["target"] for step in preset["steps"]], ["service:lead.create", "chatballs:entity_link.create"])
        self.assertEqual({item["name"] for item in preset["parameters"]}, {"owner", "stage"})
        self.assertEqual(preset["requiredPermissions"], ["crm", "user"])
        self.assertEqual(preset["requiredConnections"], ["self"])
        self.assertEqual(preset["triggers"], [{"kind": "staff"}])
        self.assertEqual(preset["steps"][0]["inputs"]["fields"]["ASSIGNED_BY_ID"], {"source": "parameter", "name": "owner"})
        operation = next(item for item in adapter["operations"] if item["key"] == "lead.create")
        self.assertEqual(operation["input"]["type"], "object")
        self.assertEqual(operation["output"]["type"], "integer")
        self.assertIn("create", {operation["effect"] for operation in adapter["operations"]})
        self.assertEqual(adapter["unsupported"][0]["capability"], "events")

    def test_connection_is_checked_by_reading_and_keeps_the_secret_on_the_server(self) -> None:
        payload = self._connected()

        (request,) = self.service.requests
        self.assertEqual((request.method, request.url), ("POST", f"{WEBHOOK}scope.json"))
        self.assertEqual(
            {key: payload[key] for key in ("adapter", "status", "isActive", "host", "hasCredentials")},
            {"adapter": "bitrix24", "status": "ok", "isActive": True, "host": "nord.bitrix24.ru", "hasCredentials": True},
        )
        self.assertNotIn(SECRET, json.dumps(payload))
        listed = self.client.get(f"{URL}services/").content.decode() + self.client.get(URL).content.decode()
        self.assertNotIn(SECRET, listed)
        row = ServiceConnectionSettings.objects.get()
        self.assertEqual(json.loads(row.credentials), {"url": WEBHOOK})
        with connection.cursor() as cursor:
            cursor.execute("SELECT credentials FROM integrations_serviceconnectionsettings WHERE id = %s", [row.id])
            self.assertNotIn(SECRET, cursor.fetchone()[0])
        integration = row.integration
        self.assertEqual((integration.kind, integration.provider, integration.channel_id), (IntegrationKind.SERVICE, IntegrationProvider.ADAPTER, None))
        audit = AuditEvent.objects.get(action="integrations.service_connected")
        self.assertNotIn(SECRET, json.dumps(audit.payload))

    def test_webhook_without_crm_access_does_not_create_a_connection(self) -> None:
        self.service.routes["/scope.json"] = json_response({"result": ["task"]})

        response = self._connect()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            {"code": "crm_access_missing", "title": t("services.bitrix24.error_crm_title"), "text": t("services.bitrix24.error_crm_text")},
        )
        self.assertFalse(Integration.objects.filter(provider=IntegrationProvider.ADAPTER).exists())

    def test_wrong_link_is_refused_before_any_request(self) -> None:
        response = self._connect(url="https://nord.bitrix24.ru/crm/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"], {"url": [t("services.bitrix24.webhook_url_invalid")]})
        self.assertEqual(self.service.requests, [])

    def test_several_connections_of_one_adapter_differ_by_name(self) -> None:
        self._connected(name="Отдел продаж")
        self._connected(name="Поддержка", url="https://help.bitrix24.ru/rest/7/OtherSecretKey77/")

        taken = self._connect(name="Отдел продаж")

        self.assertEqual(taken.status_code, 400)
        self.assertEqual(taken.json()["errors"], {"name": [t("services.name_taken")]})
        names = [item["name"] for item in self.client.get(f"{URL}services/").json()["items"]]
        self.assertEqual(names, ["Отдел продаж", "Поддержка"])

    def test_pause_resume_and_rename(self) -> None:
        connection_id = self._connected()["id"]

        paused = self.client.patch(f"{URL}services/{connection_id}/", {"isActive": False}, format="json")
        resumed = self.client.patch(f"{URL}services/{connection_id}/", {"isActive": True, "name": "CRM"}, format="json")

        self.assertFalse(paused.json()["connection"]["isActive"])
        self.assertEqual((resumed.json()["connection"]["isActive"], resumed.json()["connection"]["name"]), (True, "CRM"))
        actions = list(AuditEvent.objects.filter(action__startswith="integrations.service_").order_by("id").values_list("action", flat=True))
        self.assertEqual(
            actions,
            ["integrations.service_connected", "integrations.service_paused", "integrations.service_renamed", "integrations.service_resumed"],
        )

    def test_lost_access_is_shown_and_restored_by_replacing_access(self) -> None:
        connection_id = self._connected()["id"]
        self.service.routes["/scope.json"] = json_response({"error": "invalid_token", "error_description": "x"}, status=401)

        checked = self.client.post(f"{URL}services/{connection_id}/check/", {}, format="json")

        self.assertEqual(checked.status_code, 400)
        self.assertEqual(checked.json()["connection"]["status"], "lost")
        self.assertEqual(checked.json()["connection"]["error"]["title"], t("services.bitrix24.error_link_title"))
        self.service.routes["/scope.json"] = json_response({"result": ["crm", "user"]})
        new_link = "https://nord.bitrix24.ru/rest/1/RenewedKey9000/"

        replaced = self.client.post(f"{URL}services/{connection_id}/access/", {"values": {"url": new_link}}, format="json")

        self.assertEqual(replaced.status_code, 200, replaced.content)
        self.assertEqual(replaced.json()["connection"]["status"], "ok")
        self.assertEqual(json.loads(ServiceConnectionSettings.objects.get().credentials), {"url": new_link})

    def test_delete_removes_only_the_connection(self) -> None:
        connection_id = self._connected()["id"]

        response = self.client.delete(f"{URL}services/{connection_id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Integration.objects.filter(id=connection_id).exists())
        self.assertFalse(ServiceConnectionSettings.objects.exists())
        self.assertEqual(len(self.service.requests), 1)

    def test_lookup_is_loaded_by_a_read_operation(self) -> None:
        connection_id = self._connected()["id"]
        self.service.routes["/user.get.json"] = json_response({"result": [{"ID": "5", "NAME": "Анна", "LAST_NAME": "Смирнова"}]})

        response = self.client.get(f"{URL}services/{connection_id}/lookups/users/")

        self.assertEqual(response.json()["items"], [{"value": "5", "label": "Анна Смирнова"}])
        self.assertEqual(json.loads(self.service.requests[-1].body), {"FILTER": {"ACTIVE": True}})

    def test_paused_connection_does_not_run_operations(self) -> None:
        connection_id = self._connected()["id"]
        self.client.patch(f"{URL}services/{connection_id}/", {"isActive": False}, format="json")

        response = self.client.get(f"{URL}services/{connection_id}/lookups/users/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.service.requests), 1)

    def test_missing_user_permission_does_not_claim_that_crm_access_is_missing(self) -> None:
        connection_id = self._connected()["id"]
        self.service.routes["/user.get.json"] = json_response({"error": "insufficient_scope"}, status=401)
        response = self.client.get(f"{URL}services/{connection_id}/lookups/users/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "user_access_missing")
        self.assertEqual(response.json()["error"]["text"], t("services.bitrix24.error_users_text"))
        self.assertNotEqual(response.json()["error"]["title"], t("services.bitrix24.error_crm_title"))

    def test_generic_integration_api_does_not_create_or_change_services(self) -> None:
        created = self.client.post(URL, {"provider": "ADAPTER", "name": "x"}, format="json")
        connection_id = self._connected()["id"]
        patched = self.client.patch(f"{URL}{connection_id}/", {"name": "y"}, format="json")

        self.assertEqual((created.status_code, patched.status_code), (400, 400))

    def test_other_organization_and_employees_without_rights_are_refused(self) -> None:
        connection_id = self._connected()["id"]
        other = Organization.objects.create(name="Other", slug="service-other")
        stranger = HumanUser.objects.create_user(email="service-stranger@example.com")
        OrganizationMembership.objects.create(organization=other, user=stranger, role=EmployeeRole.OWNER, position_title="Owner")
        employee = HumanUser.objects.create_user(email="service-employee@example.com")
        OrganizationMembership.objects.create(
            organization=self.organization, user=employee, role=EmployeeRole.EMPLOYEE, position_title="Оператор"
        )
        foreign = TenantAPIClient()
        foreign.force_authenticate(stranger)
        staff = TenantAPIClient()
        staff.force_authenticate(employee)

        foreign_list = foreign.get(f"/api/v1/organizations/{other.public_id}/integrations/services/")
        foreign_detail = foreign.get(f"/api/v1/organizations/{other.public_id}/integrations/services/{connection_id}/")
        staff_create = staff.post(f"{URL}services/", {"adapter": "bitrix24"}, format="json")
        staff_delete = staff.delete(f"{URL}services/{connection_id}/")

        self.assertEqual(foreign_list.json()["items"], [])
        self.assertEqual(foreign_detail.status_code, 404)
        self.assertEqual((staff_create.status_code, staff_delete.status_code), (403, 403))
        self.assertTrue(Integration.objects.filter(id=connection_id).exists())
