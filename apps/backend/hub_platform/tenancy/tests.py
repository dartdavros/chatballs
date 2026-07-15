import json

from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient as RawAPIClient

from hub_platform.events.models import EventOwnership
from hub_platform.events.services import DomainEvent, enqueue_event, tenant_context_for_event
from hub_platform.identity.models import (
    Department,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.products.models import Product
from hub_platform.tenancy.context import TenantContext
from hub_platform.testing import TenantAPIClient


class TenantHttpBoundaryTests(TestCase):
    def setUp(self) -> None:
        self.first = Organization.objects.create(name="First", slug="first")
        self.second = Organization.objects.create(name="Second", slug="second")
        self.outside = Organization.objects.create(name="Outside", slug="outside")
        self.user = HumanUser.objects.create_user(
            email="multi@example.test", password="Password-123"
        )
        self.first_membership = self._membership(self.first)
        self.second_membership = self._membership(self.second)
        self.first_department = Department.objects.create(
            organization=self.first, code="sales", name="First Sales"
        )
        self.second_department = Department.objects.create(
            organization=self.second, code="sales", name="Second Sales"
        )
        self.first_product = Product.objects.create(
            organization=self.first, code="first-product", name="First Product"
        )
        self.second_product = Product.objects.create(
            organization=self.second, code="second-product", name="Second Product"
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.user)

    def _membership(self, organization: Organization) -> OrganizationMembership:
        return OrganizationMembership.objects.create(
            user=self.user,
            organization=organization,
            role=EmployeeRole.OWNER,
            position_title="Owner",
        )

    def _products_path(self, organization: Organization, suffix: str = "") -> str:
        return (
            f"/api/v1/organizations/{organization.public_id}/company/products/{suffix}"
        )

    def test_same_user_can_open_each_membership_without_session_singleton(self) -> None:
        first = self.client.get(self._products_path(self.first))
        second = self.client.get(self._products_path(self.second))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            [item["code"] for item in first.json()["items"]], ["first-product"]
        )
        self.assertEqual(
            [item["code"] for item in second.json()["items"]], ["second-product"]
        )

    def test_foreign_resource_id_is_not_visible_in_selected_organization(self) -> None:
        response = self.client.get(
            self._products_path(self.first, f"{self.second_product.id}/")
        )
        self.assertEqual(response.status_code, 404)

    def test_absent_blocked_and_mfa_unsatisfied_memberships_fail_closed(self) -> None:
        absent = self.client.get(self._products_path(self.outside))
        self.assertEqual(absent.status_code, 404)

        self.second_membership.block()
        blocked = self.client.get(self._products_path(self.second))
        self.assertEqual(blocked.status_code, 404)

        self.second_membership.unblock()
        self.second_membership.totp_required = True
        self.second_membership.save(update_fields=["totp_required"])
        missing_mfa = self.client.get(self._products_path(self.second))
        self.assertEqual(missing_mfa.status_code, 404)

        self.user.totp_enabled = True
        self.user.save(update_fields=["totp_enabled"])
        allowed = self.client.get(self._products_path(self.second))
        self.assertEqual(allowed.status_code, 200)

    def test_legacy_and_malformed_tenant_routes_are_not_runtime_aliases(self) -> None:
        raw_client = RawAPIClient()
        raw_client.force_login(self.user)

        self.assertEqual(raw_client.get("/api/v1/company/products/").status_code, 404)
        self.assertEqual(
            raw_client.get("/api/v1/organizations/not-a-uuid/company/products/").status_code,
            404,
        )

    def test_global_login_returns_all_memberships_without_active_tenant(self) -> None:
        client = RawAPIClient()
        response = client.post(
            "/api/v1/auth/login/",
            data=json.dumps(
                {"email": self.user.email, "password": "Password-123"}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["user"]
        self.assertNotIn("organizationPublicId", payload)
        self.assertNotIn("role", payload)
        self.assertEqual(
            {item["organizationPublicId"] for item in payload["memberships"]},
            {str(self.first.public_id), str(self.second.public_id)},
        )


class TenantEventBoundaryTests(TestCase):
    def setUp(self) -> None:
        self.first = Organization.objects.create(name="First", slug="event-first")
        self.second = Organization.objects.create(name="Second", slug="event-second")
        self.user = HumanUser.objects.create_user(email="event@example.test")
        self.membership = OrganizationMembership.objects.create(
            organization=self.first,
            user=self.user,
            role=EmployeeRole.OWNER,
            position_title="Owner",
        )

    def _event(self):
        return enqueue_event(
            DomainEvent(
                aggregate_type="Example",
                aggregate_id="1",
                event_type="example.created",
                payload={},
                tenant_context=TenantContext.for_membership(self.membership),
            )
        )

    def test_tenant_event_persists_and_revalidates_context(self) -> None:
        event = self._event()
        self.assertEqual(event.ownership, EventOwnership.TENANT)
        self.assertEqual(event.organization, self.first)
        self.assertEqual(event.membership, self.membership)

        context = tenant_context_for_event(event)
        self.assertEqual(context.organization, self.first)
        self.assertEqual(context.membership, self.membership)
        self.assertEqual(context.actor_user, self.user)

    def test_tenant_event_rejects_cross_organization_membership(self) -> None:
        event = self._event()
        event.organization = self.second
        with self.assertRaises(DatabaseError), transaction.atomic():
            event.save(update_fields=["organization"])

    def test_tenant_event_rejects_membership_blocked_after_enqueue(self) -> None:
        event = self._event()
        self.membership.block()

        with self.assertRaises(OrganizationMembership.DoesNotExist):
            tenant_context_for_event(event)

    def test_platform_event_cannot_smuggle_tenant_ownership(self) -> None:
        event = enqueue_event(
            DomainEvent(
                aggregate_type="PlatformExample",
                aggregate_id="1",
                event_type="platform.example",
                payload={},
            )
        )
        event.organization = self.first
        with self.assertRaises(IntegrityError), transaction.atomic():
            event.save(update_fields=["organization"])
