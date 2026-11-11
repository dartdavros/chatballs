"""Small picker summaries and on-demand forms recheck current availability."""

from unittest.mock import patch

from chatballs.conversations.models import Conversation
from chatballs.i18n import t
from chatballs.integrations.execution.manual_catalog_queries import catalog
from chatballs.integrations.execution.manual_catalog_testing import ManualCatalogCase
from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.models import Integration, ServiceConnectionSettings
from chatballs.tenancy.database import tenant_atomic


class ManualCatalogDetailTests(ManualCatalogCase):
    def test_summary_omits_form_schemas_files_plans_and_contact_values(self):
        with tenant_atomic(self.context):
            self.scenario()
        with patch("chatballs.integrations.execution.manual_catalog_queries.field_payload", side_effect=AssertionError("schema")), patch(
                "chatballs.integrations.execution.manual_catalog_queries.parameter_schema", side_effect=AssertionError("schema")), patch(
                "chatballs.integrations.execution.manual_catalog_queries.allowed_files", side_effect=AssertionError("files")), patch(
                "chatballs.integrations.execution.manual_catalog_queries.initial_values", side_effect=AssertionError("values")):
            summary = self.menu(summary="1")
        self.assertEqual(summary["files"], [])
        self.assertTrue(summary["items"])
        self.assertTrue(all(item["available"] is True for item in summary["items"]))
        for item in summary["items"]:
            self.assertFalse({"parameters", "initialValues", "plan"} & item.keys())

    def test_detail_keeps_existing_form_contract_and_explicit_navigation(self):
        identity = f"{self.service.pk}:lead.create"
        detail = self.menu(kind="operation", id=identity)
        self.assertEqual(set(detail), {"item", "files"})
        item = detail["item"]
        self.assertEqual(item["id"], identity)
        self.assertIn("parameters", item)
        self.assertEqual(item["initialValues"], {"fields": {"NAME": "Customer"}})
        self.assertEqual(item["presentation"], {
            "source": {"key": f"service:{self.service.pk}", "title": t("services.bitrix24.title"),
                       "subtitle": self.service.name, "kind": "service"},
            "categoryPath": [{"key": "crm", "title": "CRM"}]})
        full = self.menu()
        self.assertEqual(item, next(row for row in full["items"] if row["id"] == identity))

    def test_changed_status_between_summary_and_detail_cannot_open_a_form(self):
        identity = f"{self.service.pk}:lead.create"
        self.assertIn(identity, {row["id"] for row in self.menu(summary="1")["items"]})
        for change in ({"is_active": False}, {"is_active": True, "status": "ERROR"}):
            with tenant_atomic(self.context):
                Integration.objects.filter(pk=self.service.pk).update(**change)
            self.assertEqual(self.menu(summary="1")["items"], [])
            with self.assertRaises(ExecutionDenied):
                self.menu(kind="operation", id=identity)

    def test_connection_identity_and_scenario_category_are_stable(self):
        with tenant_atomic(self.context):
            second = Integration.objects.create(organization=self.organization, name="Second CRM", kind="SERVICE",
                provider="ADAPTER", is_active=True, status="OK")
            ServiceConnectionSettings.objects.create(integration=second, adapter_key="bitrix24", adapter_version=1,
                                                       auth_method="webhook", credentials="{}")
            categorized = self.scenario(name="Categorized")
            categorized.category_path = ["Продажи", "Лиды"]
            categorized.save(update_fields=["category_path"])
            ordinary = self.scenario(name="Uncategorized")
        items = self.menu(summary="1")["items"]
        source_keys = {item["presentation"]["source"]["key"] for item in items if item["kind"] == "operation"}
        self.assertEqual(source_keys, {f"service:{self.service.pk}", f"service:{second.pk}"})
        path = next(row["presentation"]["categoryPath"] for row in items if row["id"] == str(categorized.public_id))
        self.assertEqual([part["title"] for part in path], ["Продажи", "Лиды"])
        self.assertNotEqual(path[0]["key"], path[1]["key"])
        path = next(row["presentation"]["categoryPath"] for row in items if row["id"] == str(ordinary.public_id))
        self.assertEqual(path, [{"key": "uncategorized", "title": t("runs.catalog_uncategorized")}])

    def test_invalid_or_foreign_dialog_never_falls_back_to_global_actions(self):
        for raw in ("", "bad", "0.5", "-1", "1234567890123456", "²"):
            with self.subTest(raw=raw), self.assertRaises(ExecutionDenied), patch(
                    "chatballs.integrations.action_catalog.manual_catalog.manual_actions", side_effect=AssertionError("global fallback")):
                catalog(self.context, {"conversation": raw, "summary": "1"})
        with self.assertRaises(Conversation.DoesNotExist):
            catalog(self.context, {"conversation": str(self.foreign_conversation.pk), "summary": "1"})

    def test_missing_or_invalid_selection_is_rejected(self):
        for query in ({"id": "1:lead.create"}, {"kind": "scenario"}, {"kind": "scenario", "id": "bad"},
                      {"kind": "operation", "id": "chatballs:comments.get"}):
            with self.subTest(query=query), self.assertRaises(ExecutionDenied):
                self.menu(**query)
