from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from chatballs.identity.group_models import EmployeeGroup, EmployeeGroupMember
from chatballs.identity.group_services import create_group, delete_group, update_group
from chatballs.identity.models import HumanUser, Organization, OrganizationMembership
from chatballs.tenancy.context import TenantContext


class OwnerGroupProtectionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Groups", slug="protected-owner-groups")
        self.owner = self.member("owner@groups.test", "OWNER")
        self.admin = self.member("admin@groups.test", "ADMIN")
        self.context = TenantContext.for_membership(self.admin)
        self.group = EmployeeGroup.objects.create(organization=self.organization, name="Support")
        EmployeeGroupMember.objects.create(
            organization=self.organization, group=self.group, employee=self.owner,
        )

    def member(self, email, role):
        user = HumanUser.objects.create_user(email=email)
        return OrganizationMembership.objects.create(organization=self.organization, user=user, role=role)

    def test_owner_cannot_be_added_or_removed_through_group_commands(self):
        for action in (
            lambda: create_group(self.context, {"name": "Other", "memberIds": [self.owner.user_id]}),
            lambda: update_group(self.context, self.group.id, {"memberIds": []}),
            lambda: delete_group(self.context, self.group.id),
        ):
            with self.subTest(action=action), self.assertRaises(PermissionDenied):
                action()
        self.assertTrue(self.group.member_links.filter(employee=self.owner).exists())

    def test_admin_can_edit_group_without_changing_owner_membership(self):
        update_group(self.context, self.group.id, {
            "name": "Renamed", "memberIds": [self.owner.user_id, self.admin.user_id],
        })
        self.assertEqual(self.group.member_links.count(), 2)
