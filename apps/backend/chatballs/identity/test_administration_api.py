from __future__ import annotations

from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from chatballs.identity.audit import record_audit_event
from chatballs.identity.bootstrap import bootstrap_owner
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.testing import TenantAPIClient


class AdministrationApiTests(TestCase):
    def setUp(self) -> None:
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

        self.organization = Organization.objects.create(
            name="Example",
            slug="administration",
            timezone="Europe/Moscow",
            currency="RUB",
        )
        self.owner = HumanUser.objects.create_user(
            email="owner@administration.test",
            password="Password-123",
            full_name="Владелец",
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=EmployeeRole.OWNER,
            position_title="Владелец",
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.owner)

    @override_settings(CHATBALLS_DELIVERY_MODE="CLOUD")
    def test_session_exposes_delivery_mode_without_installation_inference(self) -> None:
        response = self.client.get("/api/v1/auth/session/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["deliveryMode"], "CLOUD")

    def test_settings_payload_contains_only_current_administration_fields(self) -> None:
        response = self.client.get("/api/v1/company/administration/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["organization"],
            {
                "name": "Example",
                "timezone": "Europe/Moscow",
                "currency": "RUB",
                # Пустой язык — «как в установке»: организация своего не выбрала.
                "language": "",
                "logoUrl": None,
                # Подпись «Сохранено …» у кнопки (кадр N1): пока правок не было — null.
                "updatedAt": None,
            },
        )
        self.assertIn("Europe/Moscow", response.json()["timezones"])
        self.assertGreater(len(response.json()["timezones"]), 300)
        self.assertNotIn("taxRegime", response.json()["organization"])

    def test_owner_updates_current_organization(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/",
            {
                "name": "Новая компания",
                "timezone": "Asia/Yekaterinburg",
                "currency": "rub",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.name, "Новая компания")
        self.assertEqual(self.organization.timezone, "Asia/Yekaterinburg")
        self.assertEqual(self.organization.currency, "RUB")

    def test_invalid_timezone_is_rejected(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/",
            {"timezone": "Nowhere/Invalid"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("timezone", response.json()["errors"])

    def test_only_ruble_currency_is_accepted(self) -> None:
        response = self.client.patch(
            "/api/v1/company/administration/",
            {"currency": "USD"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("российский рубль", response.json()["errors"]["currency"])

    def test_logo_upload_download_and_delete(self) -> None:
        png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        uploaded = self.client.post(
            "/api/v1/company/administration/logo/",
            {"file": SimpleUploadedFile("logo.png", png, content_type="image/png")},
            format="multipart",
        )

        self.assertEqual(uploaded.status_code, 200)
        logo_url = uploaded.json()["organization"]["logoUrl"]
        self.assertTrue(logo_url.endswith("/company/administration/logo/"))
        session = self.client.get("/api/v1/auth/session/")
        self.assertEqual(
            session.json()["user"]["memberships"][0]["organizationLogoUrl"],
            logo_url,
        )

        downloaded = self.client.get("/api/v1/company/administration/logo/")
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["Content-Type"], "image/png")
        self.assertEqual(b"".join(downloaded.streaming_content), png)

        deleted = self.client.delete("/api/v1/company/administration/logo/")
        self.assertEqual(deleted.status_code, 200)
        self.assertIsNone(deleted.json()["organization"]["logoUrl"])

    def test_profile_avatar_upload_visible_to_colleagues(self) -> None:
        png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        uploaded = self.client.post(
            "/api/v1/auth/profile/avatar/",
            {"file": SimpleUploadedFile("me.png", png, content_type="image/png")},
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, 200)
        own_url = uploaded.json()["user"]["avatarUrl"]
        self.assertTrue(own_url.startswith("/api/v1/auth/profile/avatar/?v="))
        self.assertEqual(self.client.get("/api/v1/auth/profile/avatar/").status_code, 200)

        # Коллеги видят фото через тенантный эндпоинт; ссылка приходит в списке сотрудников.
        employees = self.client.get("/api/v1/employees/").json()["items"]
        colleague_url = employees[0]["avatarUrl"]
        self.assertIn(f"/employees/{self.owner.id}/avatar/", colleague_url)
        self.assertEqual(self.client.get(colleague_url.split("?")[0]).status_code, 200)

        removed = self.client.delete("/api/v1/auth/profile/avatar/")
        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.json()["user"]["avatarUrl"])
        self.assertEqual(self.client.get("/api/v1/auth/profile/avatar/").status_code, 404)

    def test_group_color_is_stored_and_validated(self) -> None:
        created = self.client.post(
            "/api/v1/company/groups/", {"name": "Операторы", "color": "#2AA876"}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["group"]["color"], "#2aa876")
        bad = self.client.post("/api/v1/company/groups/", {"name": "Плохая", "color": "red"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_non_image_logo_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/company/administration/logo/",
            {
                "file": SimpleUploadedFile(
                    "logo.svg",
                    b"<svg></svg>",
                    content_type="image/svg+xml",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("PNG, JPEG и WebP", response.json()["detail"])

    def test_audit_returns_readable_label_next_to_the_action_code(self) -> None:
        record_audit_event(
            action="administration.organization_updated",
            actor=self.owner,
            organization=self.organization,
            object_type="Organization",
            object_id="42",
        )

        response = self.client.get("/api/v1/company/administration/audit/")

        self.assertEqual(response.status_code, 200)
        event = response.json()["items"][0]
        self.assertEqual(event["actionLabel"], "Изменены данные организации")
        # Код действия нужен для поиска, поэтому уезжает рядом с подписью.
        self.assertEqual(event["action"], "administration.organization_updated")
        self.assertEqual(event["categoryLabel"], "Настройки")
        self.assertEqual(event["object"], "Организация · 42")

    def test_audit_shows_the_raw_code_when_the_action_has_no_label(self) -> None:
        """Действие без подписи должно быть видно кодом, а не схлопываться в
        «Системное действие» вместе со всеми остальными."""

        record_audit_event(
            action="ai.brand_new_thing",
            actor=self.owner,
            organization=self.organization,
        )

        event = self.client.get("/api/v1/company/administration/audit/").json()["items"][0]

        self.assertEqual(event["actionLabel"], "")
        self.assertEqual(event["action"], "ai.brand_new_thing")
        self.assertEqual(event["categoryLabel"], "AI и знания")

    def test_audit_filters_by_category_result_actor_and_search(self) -> None:
        record_audit_event(
            action="administration.organization_updated",
            actor=self.owner,
            organization=self.organization,
        )
        record_audit_event(
            action="ai.knowledge_created",
            organization=self.organization,
            object_type="Knowledge",
            object_id="7",
        )
        record_audit_event(
            action="identity.login_failed",
            actor=self.owner,
            organization=self.organization,
            result="FAILED",
        )
        url = "/api/v1/company/administration/audit/"

        by_category = self.client.get(url, {"category": "ai"}).json()
        self.assertEqual(by_category["total"], 1)
        self.assertEqual(by_category["items"][0]["action"], "ai.knowledge_created")

        by_result = self.client.get(url, {"result": "FAILED"}).json()
        self.assertEqual(by_result["total"], 1)
        self.assertEqual(by_result["items"][0]["action"], "identity.login_failed")

        by_system_actor = self.client.get(url, {"actor": "system"}).json()
        self.assertEqual(by_system_actor["total"], 1)
        self.assertEqual(by_system_actor["items"][0]["actor"], "Система")

        by_search = self.client.get(url, {"q": "knowledge"}).json()
        self.assertEqual(by_search["total"], 1)
        self.assertEqual(by_search["items"][0]["action"], "ai.knowledge_created")

    def test_audit_conversation_prefix_synonym_lands_in_the_dialogs_category(self) -> None:
        """Часть кода пишет conversation.*, часть conversations.* — в фильтре
        «Диалоги» должны быть оба."""

        record_audit_event(
            action="conversation.contact_updated",
            organization=self.organization,
        )
        record_audit_event(
            action="conversations.claimed",
            organization=self.organization,
        )

        payload = self.client.get(
            "/api/v1/company/administration/audit/", {"category": "conversations"}
        ).json()

        self.assertEqual(payload["total"], 2)

    def test_audit_pages_through_the_whole_journal(self) -> None:
        """Раньше отдавались последние 50 событий и дальше журнала не было."""

        for index in range(60):
            record_audit_event(
                action="identity.login_succeeded",
                actor=self.owner,
                organization=self.organization,
                object_id=str(index),
            )
        url = "/api/v1/company/administration/audit/"

        first = self.client.get(url, {"pageSize": 25}).json()
        self.assertEqual(first["total"], 60)
        self.assertEqual(first["pageCount"], 3)
        self.assertEqual(len(first["items"]), 25)

        last = self.client.get(url, {"pageSize": 25, "page": 3}).json()
        self.assertEqual(len(last["items"]), 10)
        # Страница за пределами журнала возвращает последнюю, а не пустоту.
        self.assertEqual(self.client.get(url, {"pageSize": 25, "page": 99}).json()["page"], 3)

    def test_audit_actor_filter_lists_every_employee_once(self) -> None:
        """У AuditEvent есть Meta.ordering, и без её сброса DISTINCT считает
        уникальность вместе с created_at — сотрудник попадал в фильтр столько
        раз, сколько совершил действий."""

        for index in range(5):
            record_audit_event(
                action="identity.login_succeeded",
                actor=self.owner,
                organization=self.organization,
                object_id=str(index),
            )
        record_audit_event(action="demo.installed", organization=self.organization)

        actors = self.client.get(
            "/api/v1/company/administration/audit/"
        ).json()["filters"]["actors"]

        values = [actor["value"] for actor in actors]
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(values.count(str(self.owner.id)), 1)
        self.assertEqual(values.count("system"), 1)

    def test_audit_filter_lists_have_no_duplicates(self) -> None:
        """Все три списка фильтров — без повторов. Сотрудники считаются из базы
        и однажды дублировались (см. тест выше); разделы и результаты приходят
        из каталога, и повтор там означал бы задвоенный ключ в словаре."""

        for action in ("identity.login_succeeded", "ai.knowledge_created", "demo.installed"):
            for _ in range(3):
                record_audit_event(
                    action=action, actor=self.owner, organization=self.organization
                )

        filters = self.client.get(
            "/api/v1/company/administration/audit/"
        ).json()["filters"]

        for name, options in filters.items():
            values = [option["value"] for option in options]
            labels = [option["label"] for option in options]
            self.assertEqual(len(values), len(set(values)), f"повторы значений в {name}")
            self.assertEqual(len(labels), len(set(labels)), f"повторы подписей в {name}")

    def test_audit_filter_lists_cover_the_whole_journal_not_the_current_page(self) -> None:
        record_audit_event(
            action="ai.knowledge_created", organization=self.organization
        )
        record_audit_event(
            action="identity.login_succeeded", actor=self.owner, organization=self.organization
        )

        filters = self.client.get(
            "/api/v1/company/administration/audit/", {"category": "ai"}
        ).json()["filters"]

        actor_labels = {actor["label"] for actor in filters["actors"]}
        self.assertIn("Система", actor_labels)
        self.assertTrue(any(actor["value"].isdigit() for actor in filters["actors"]))
        self.assertIn(
            "Диалоги", {category["label"] for category in filters["categories"]}
        )


class InstanceAddressTests(TestCase):
    """Адрес установки правится в «Настройках», а не в переменных окружения."""

    def setUp(self) -> None:
        result = bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.organization = result.organization
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)

    def test_owner_sets_domain_and_scheme(self) -> None:
        response = self.client.patch(
            "/api/v1/instance/settings/",
            {"publicHost": "crm.example.com", "publicScheme": "https"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["instance"]
        self.assertEqual(body["publicHost"], "crm.example.com")
        self.assertEqual(body["publicUrl"], "https://crm.example.com")

    def test_address_may_be_a_bare_ip(self) -> None:
        # Коробку часто так и оставляют: сервер по IP, без домена.
        response = self.client.patch(
            "/api/v1/instance/settings/",
            {"publicHost": "203.0.113.10", "publicScheme": "http"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["instance"]["publicUrl"], "http://203.0.113.10")

    def test_url_is_accepted_and_trimmed_to_host(self) -> None:
        response = self.client.patch(
            "/api/v1/instance/settings/",
            {"publicHost": "https://crm.example.com/settings", "publicScheme": "https"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["instance"]["publicHost"], "crm.example.com")

    def test_garbage_is_rejected(self) -> None:
        response = self.client.patch(
            "/api/v1/instance/settings/",
            {"publicHost": "не адрес!", "publicScheme": "ftp"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)


class InstanceEmailTests(TestCase):
    """Почта установки задаётся в «Настройках»: без неё некого приглашать."""

    def setUp(self) -> None:
        result = bootstrap_owner(email="owner@example.com", password="temporary-password")
        self.client = TenantAPIClient()
        self.client.force_authenticate(result.owner)

    def patch(self, **email):
        return self.client.patch(
            "/api/v1/instance/settings/",
            {"publicHost": "crm.example.com", "publicScheme": "https", "email": email},
            format="json",
        )

    def test_smtp_is_saved_and_password_is_not_returned(self) -> None:
        response = self.patch(
            host="smtp.example.com",
            port=465,
            user="robot@example.com",
            password="s3cret",
            useTls=True,
            **{"from": "Chatballs <robot@example.com>"},
        )

        self.assertEqual(response.status_code, 200, response.content)
        email = response.json()["instance"]["email"]
        self.assertEqual(email["host"], "smtp.example.com")
        self.assertEqual(email["port"], 465)
        self.assertTrue(email["configured"])
        self.assertTrue(email["hasPassword"])
        self.assertNotIn("password", email)

    def test_empty_password_keeps_the_stored_one(self) -> None:
        self.patch(host="smtp.example.com", password="s3cret")

        response = self.patch(host="smtp.example.com", password="")

        self.assertTrue(response.json()["instance"]["email"]["hasPassword"])

    def test_check_without_smtp_explains_itself(self) -> None:
        response = self.client.post(
            "/api/v1/instance/settings/email-check/", {}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("сервер исходящей почты", response.json()["detail"])
