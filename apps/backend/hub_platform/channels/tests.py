import json

from django.test import TestCase
from rest_framework.test import APIClient

from hub_platform.channels.models import Channel
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import EmployeeProfile, EmployeeRole, HumanUser, Organization


def _make_channel(organization, *, code, name):
    return Channel.objects.create(organization=organization, code=code, name=name)


class ChannelRenameTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.channel = _make_channel(self.organization, code="firepage-sales", name="FirePage — продажи")
        self.client = APIClient()
        self.client.login(username="owner@edevs.tech", password="temporary-password")

    def test_owner_renames_channel(self) -> None:
        response = self.client.patch(
            f"/api/v1/channels/{self.channel.id}/",
            data=json.dumps({"name": "FirePage — продажи 2"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["channel"]["name"], "FirePage — продажи 2")
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.name, "FirePage — продажи 2")
        # code не меняется (нельзя ломать embed-сниппеты data-channel).
        self.assertEqual(self.channel.code, "firepage-sales")

    def test_rename_rejects_empty_name(self) -> None:
        response = self.client.patch(
            f"/api/v1/channels/{self.channel.id}/",
            data=json.dumps({"name": "   "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_other_organization_channel_is_not_found(self) -> None:
        other = Organization.objects.create(slug="other", name="Other")
        other_channel = _make_channel(other, code="other-sales", name="Other — продажи")

        response = self.client.patch(
            f"/api/v1/channels/{other_channel.id}/",
            data=json.dumps({"name": "Взлом"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        other_channel.refresh_from_db()
        self.assertEqual(other_channel.name, "Other — продажи")


class ChannelRenamePermissionTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        organization = Organization.objects.get(slug="edevs")
        self.channel = _make_channel(organization, code="firepage-sales", name="FirePage — продажи")
        operator = HumanUser.objects.create_user(email="operator@edevs.tech", password="operator-password")
        EmployeeProfile.objects.create(
            user=operator,
            organization=organization,
            role=EmployeeRole.OPERATOR,
            department=None,
        )
        self.client = APIClient()
        self.client.login(username="operator@edevs.tech", password="operator-password")

    def test_operator_cannot_rename_channel(self) -> None:
        response = self.client.patch(
            f"/api/v1/channels/{self.channel.id}/",
            data=json.dumps({"name": "Взлом"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
