from django.test import TestCase
from django.utils import timezone

from chatballs.identity.instance_access import can_manage_platform
from chatballs.identity.instance_settings import InstanceSettings, invalidate_cache
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.testing import TenantAPIClient


class PlatformAuthorityTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Platform", slug="platform-authority")
        self.user = HumanUser.objects.create_user(email="admin@platform.test")
        self.membership = OrganizationMembership.objects.create(
            organization=self.organization, user=self.user, role="ADMIN",
        )
        self.client = TenantAPIClient()
        self.client.force_authenticate(self.user)
        InstanceSettings.load()
        self.addCleanup(invalidate_cache)

    def test_admin_manages_platform_and_authority_is_revoked_immediately(self):
        self.assertTrue(can_manage_platform(self.user))
        response = self.client.patch("/api/v1/instance/settings/", {
            "externalChecksEnabled": False,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.membership.blocked_at = timezone.now()
        self.membership.save(update_fields=["blocked_at"])
        self.assertFalse(can_manage_platform(self.user))
        self.assertEqual(self.client.get("/api/v1/instance/settings/").status_code, 403)

    def test_turn_authority_cannot_be_bypassed_in_mixed_platform_patch(self):
        original_host = InstanceSettings.objects.get(pk=1).public_host
        response = self.client.patch("/api/v1/instance/settings/", {
            "publicHost": "new.example.test", "turn": {},
        }, format="json")
        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(InstanceSettings.objects.get(pk=1).public_host, original_host)

    def test_employee_has_no_platform_authority(self):
        self.membership.role = "EMPLOYEE"
        self.membership.save(update_fields=["role"])
        self.assertFalse(can_manage_platform(self.user))
        self.assertEqual(self.client.get("/api/v1/instance/update/announcements/").status_code, 403)
