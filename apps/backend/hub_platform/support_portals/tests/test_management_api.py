from unittest import mock

from django.conf import settings
from django.test import override_settings

from hub_platform.channels.models import Channel
from hub_platform.identity.capabilities import ScopeType
from hub_platform.identity.models import (
    AccessProfile,
    AccessProfileCapability,
    EmployeeAccessAssignment,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.subscriptions.testing import create_test_subscription
from hub_platform.support_portals.models import SupportPortal, SupportPortalProduct
from hub_platform.support_portals.tests.base import SupportPortalTestCase


class SupportPortalManagementTests(SupportPortalTestCase):
    def test_subscription_allows_multiple_active_portals(self) -> None:
        first = self.create_portal()
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()["portal"]["departmentCode"], "support")
        self.assertEqual(
            first.json()["portal"]["hostedDomain"],
            f"foxray-help.{settings.CUS_HELP_BASE_DOMAIN}",
        )
        self.assertTrue(first.json()["portal"]["publicUrl"].endswith(
            f"foxray-help.{settings.CUS_HELP_BASE_DOMAIN}"
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
        response = self.client.put(
            f"/api/v1/support/portals/{portal_id}/products/",
            {
                "items": [
                    {
                        "productId": self.product.id,
                        "supportChannelId": self.channel.id,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        link = SupportPortalProduct.objects.get()
        self.assertEqual(link.product, self.product)
        self.assertEqual(link.support_channel, self.channel)

        anonymous_channel = Channel.objects.create(
            organization=self.organization,
            code="anonymous-help",
            name="Anonymous",
            department=self.channel.department,
            product=self.product,
        )
        rejected = self.client.put(
            f"/api/v1/support/portals/{portal_id}/products/",
            {
                "items": [
                    {
                        "productId": self.product.id,
                        "supportChannelId": anonymous_channel.id,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(rejected.status_code, 400, rejected.content)
        link.refresh_from_db()
        self.assertEqual(link.support_channel, self.channel)

    def test_custom_domain_requires_matching_dns_record(self) -> None:
        portal_id = self.create_portal().json()["portal"]["id"]
        configured = self.client.put(
            f"/api/v1/support/portals/{portal_id}/domain/",
            {"customDomain": "help.customer.example"},
            format="json",
        )
        self.assertEqual(configured.status_code, 200, configured.content)
        verification = configured.json()["portal"]["customDomainVerification"]
        answer = mock.Mock(strings=[verification["value"].encode("utf-8")])

        with mock.patch("dns.resolver.resolve", return_value=[answer]):
            verified = self.client.post(
                f"/api/v1/support/portals/{portal_id}/domain/verify/",
                {},
                format="json",
            )

        self.assertEqual(verified.status_code, 200, verified.content)
        self.assertIsNotNone(verified.json()["portal"]["customDomainVerifiedAt"])
        self.assertIsNone(verified.json()["portal"]["customDomainVerification"])

    @override_settings(CUS_APP_PRIMARY_HOSTS=["app.customer.example"])
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
        other_owner_membership = OrganizationMembership.objects.create(
            organization=other_organization,
            user=other_owner,
            role=EmployeeRole.OWNER,
        )
        other_support = other_organization.departments.create(
            code="support",
            name="Поддержка",
        )
        other_profile = AccessProfile.objects.create(
            organization=other_organization,
            name="Portal reader",
        )
        AccessProfileCapability.objects.create(
            access_profile=other_profile,
            capability_code="support.view",
        )
        EmployeeAccessAssignment.objects.create(
            employee=other_owner_membership,
            access_profile=other_profile,
            scope_type=ScopeType.DEPARTMENT,
            department=other_support,
            assigned_by=other_owner_membership,
        )
        create_test_subscription(other_organization)
        self.client.force_authenticate(other_owner)
        self.client.set_tenant(other_organization)

        response = self.client.get(f"/api/v1/support/portals/{portal_id}/")

        self.assertEqual(response.status_code, 404, response.content)

    def test_support_scope_is_required_for_portal_access(self) -> None:
        self.create_portal()
        employee_user = HumanUser.objects.create_user(
            email="scoped-portal-reader@example.com",
            password="temporary-password",
        )
        employee = OrganizationMembership.objects.create(
            organization=self.organization,
            user=employee_user,
            role=EmployeeRole.EMPLOYEE,
        )
        profile = AccessProfile.objects.create(
            organization=self.organization,
            name="Portal reader",
        )
        AccessProfileCapability.objects.create(
            access_profile=profile,
            capability_code="support.view",
        )
        sales = self.organization.departments.get(code="sales")
        assignment = EmployeeAccessAssignment.objects.create(
            employee=employee,
            access_profile=profile,
            scope_type=ScopeType.DEPARTMENT,
            department=sales,
            assigned_by=self.organization.memberships.get(user=self.owner),
        )
        self.client.force_authenticate(employee_user)
        denied = self.client.get("/api/v1/support/portals/")
        self.assertEqual(denied.status_code, 403, denied.content)

        assignment.department = self.organization.departments.get(code="support")
        assignment.save(update_fields=["department"])
        allowed = self.client.get("/api/v1/support/portals/")
        self.assertEqual(allowed.status_code, 200, allowed.content)
