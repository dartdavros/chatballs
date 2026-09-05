from unittest import mock

from django.conf import settings
from django.test import override_settings

from chatballs.channels.models import Channel
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.support_portals.models import SupportPortal, SupportPortalProduct
from chatballs.support_portals.tests.base import SupportPortalTestCase
from chatballs.webchat.testing import create_web_widget


class SupportPortalManagementTests(SupportPortalTestCase):
    def test_anonymous_web_channel_can_be_attached_as_portal_widget(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        widget_channel = Channel.objects.create(
            organization=self.organization,
            code="app-portal-chat",
            name="Acme — чат портала",
            product=self.product,
            requires_authenticated_product_identity=False,
            allow_anonymous_sessions=True,
            allow_self_reported_contact=True,
        )
        widget = create_web_widget(widget_channel, name="Acme portal widget")

        options = self.client.get(
            f"/api/v1/support/portals/{portal_id}/support-channels/"
        )
        self.assertEqual(options.status_code, 200, options.content)
        self.assertEqual(
            [item["id"] for item in options.json()["widgetItems"]],
            [widget.id],
        )

        updated = self.client.patch(
            f"/api/v1/support/portals/{portal_id}/",
            {"widgetId": widget.id},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(
            updated.json()["portal"]["widgetKey"],
            widget.public_key,
        )

        config = self.client.get(
            f"/api/v1/webchat/config/?widgetKey={widget.public_key}",
            HTTP_ORIGIN="http://app-help.localhost",
        )
        self.assertEqual(config.status_code, 200, config.content)
        self.assertTrue(config.json()["available"])

    def test_authenticated_support_channel_is_rejected_by_public_webchat(self) -> None:
        widget = create_web_widget(self.channel, name="Authenticated support widget")

        config = self.client.get(
            f"/api/v1/webchat/config/?widgetKey={widget.public_key}",
        )
        session = self.client.post(
            "/api/v1/webchat/session/",
            {"widgetKey": widget.public_key},
            format="json",
        )

        self.assertTrue(config.json()["available"])
        self.assertEqual(config.json()["mode"], "AUTHENTICATED_PRODUCT")
        self.assertEqual(session.status_code, 404, session.content)

    def test_multiple_active_portals_without_limits(self) -> None:
        # Лимитов на порталы нет (ADR-HUB-0042): creation всегда canCreate=true.
        first = self.create_portal()
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(
            first.json()["portal"]["hostedDomain"],
            f"app-help.{settings.CHATBALLS_HELP_BASE_DOMAIN}",
        )
        self.assertTrue(first.json()["portal"]["publicUrl"].endswith(
            f"app-help.{settings.CHATBALLS_HELP_BASE_DOMAIN}"
        ))

        listed = self.client.get("/api/v1/support/portals/")
        self.assertEqual(listed.status_code, 200, listed.content)
        self.assertEqual(
            listed.json()["creation"],
            {"available": True, "canCreate": True, "limit": None, "used": 1},
        )

        second = self.create_portal("another-help")
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(SupportPortal.objects.count(), 2)

    def test_product_route_requires_authenticated_support_channel(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        support_widget = create_web_widget(self.channel, name="Product support widget")
        response = self.client.put(
            f"/api/v1/support/portals/{portal_id}/products/",
            {
                "items": [
                    {
                        "productId": self.product.id,
                        "supportWidgetId": support_widget.id,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        link = SupportPortalProduct.objects.get()
        self.assertEqual(link.product, self.product)
        self.assertEqual(link.support_channel, self.channel)
        self.assertEqual(link.support_widget, support_widget)

        anonymous_channel = Channel.objects.create(
            organization=self.organization,
            code="anonymous-help",
            name="Anonymous",
            product=self.product,
        )
        anonymous_widget = create_web_widget(anonymous_channel, name="Anonymous widget")
        rejected = self.client.put(
            f"/api/v1/support/portals/{portal_id}/products/",
            {
                "items": [
                    {
                        "productId": self.product.id,
                        "supportWidgetId": anonymous_widget.id,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(rejected.status_code, 400, rejected.content)
        link.refresh_from_db()
        self.assertEqual(link.support_channel, self.channel)

    @override_settings(CHATBALLS_HELP_PUBLIC_IPV4="203.0.113.42")
    def test_custom_domain_requires_matching_dns_records(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        configured = self.client.put(
            f"/api/v1/support/portals/{portal_id}/domain/",
            {"customDomain": "help.customer.example"},
            format="json",
        )
        self.assertEqual(configured.status_code, 200, configured.content)
        verification = configured.json()["portal"]["customDomainVerification"]
        self.assertEqual(
            configured.json()["portal"]["customDomainAddress"],
            {
                "name": "help.customer.example",
                "type": "A",
                "value": "203.0.113.42",
            },
        )
        address_answer = mock.Mock(address="203.0.113.42")
        verification_answer = mock.Mock(
            strings=[verification["value"].encode("utf-8")]
        )

        with mock.patch(
            "dns.resolver.resolve",
            side_effect=[[address_answer], [verification_answer]],
        ) as resolve:
            verified = self.client.post(
                f"/api/v1/support/portals/{portal_id}/domain/verify/",
                {},
                format="json",
            )

        self.assertEqual(verified.status_code, 200, verified.content)
        self.assertIsNotNone(verified.json()["portal"]["customDomainVerifiedAt"])
        self.assertIsNone(verified.json()["portal"]["customDomainVerification"])
        self.assertEqual(
            resolve.call_args_list,
            [
                mock.call("help.customer.example", "A"),
                mock.call("_chatballs.help.customer.example", "TXT"),
            ],
        )

    @override_settings(CHATBALLS_HELP_PUBLIC_IPV4="203.0.113.42")
    def test_custom_domain_rejects_wrong_address_record(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        self.client.put(
            f"/api/v1/support/portals/{portal_id}/domain/",
            {"customDomain": "help.customer.example"},
            format="json",
        )

        with mock.patch(
            "dns.resolver.resolve",
            return_value=[mock.Mock(address="203.0.113.99")],
        ):
            response = self.client.post(
                f"/api/v1/support/portals/{portal_id}/domain/verify/",
                {},
                format="json",
            )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("указывает не на сервер Chatballs", str(response.json()))

    @override_settings(CHATBALLS_APP_PRIMARY_HOSTS=["app.customer.example"])
    def test_custom_domain_cannot_shadow_application_host(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        response = self.client.put(
            f"/api/v1/support/portals/{portal_id}/domain/",
            {"customDomain": "app.customer.example"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_portal_is_not_visible_from_another_tenant(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        other_organization = Organization.objects.create(
            slug="other-portal-tenant",
            name="Other tenant",
        )
        other_owner = HumanUser.objects.create_user(
            email="other-portal-owner@example.com",
            password="temporary-password",
        )
        OrganizationMembership.objects.create(
            organization=other_organization,
            user=other_owner,
            role=EmployeeRole.OWNER,
        )
        self.client.force_authenticate(other_owner)
        self.client.set_tenant(other_organization)

        response = self.client.get(f"/api/v1/support/portals/{portal_id}/")

        self.assertEqual(response.status_code, 404, response.content)
