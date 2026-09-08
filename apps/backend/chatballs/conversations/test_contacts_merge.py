"""Объединение и разъединение контактов (ADR-CHATBALLS-0006)."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.conversations.contacts_merge import merge_contacts, revert_merge
from chatballs.conversations.models import ConnectionIdentity, Contact, ContactMerge, Conversation
from chatballs.identity.models import (
    AuditEvent,
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from chatballs.integrations.models import Integration
from chatballs.testing import TenantAPIClient as APIClient


class ContactsMergeTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Ателье", slug="atelie")
        self.owner = HumanUser.objects.create(email="owner@atelie.test", full_name="Елена Кузнецова")
        self.channel = Channel.objects.create(organization=self.organization, code="consultant", name="Консультант")
        self.connection = Integration.objects.create(
            organization=self.organization, kind="MESSENGER", provider="TELEGRAM", name="Бот", channel=self.channel
        )
        self.target = Contact.objects.create(organization=self.organization, name="Мария Соколова", phone="+79162041187")
        self.source = Contact.objects.create(organization=self.organization, name="Гость", city="Москва")
        self.identity = ConnectionIdentity.objects.create(
            contact=self.source, connection=self.connection, external_user_id="482913001", display_name="Гость"
        )
        self.conversation = Conversation.objects.create(
            organization=self.organization, channel=self.channel, connection=self.connection, contact=self.source
        )

    def test_merge_moves_identities_and_dialogs_and_is_audited(self) -> None:
        merge = merge_contacts(
            organization=self.organization,
            target_id=self.target.id,
            source_id=self.source.id,
            reason="Один и тот же человек, совпал телефон",
            actor=self.owner,
        )

        self.identity.refresh_from_db()
        self.conversation.refresh_from_db()
        self.source.refresh_from_db()
        self.target.refresh_from_db()
        self.assertEqual(self.identity.contact_id, self.target.id)
        self.assertEqual(self.conversation.contact_id, self.target.id)
        self.assertEqual(self.source.merged_into_id, self.target.id)
        # Пустое поле целевого контакта дозаполнено из исходного.
        self.assertEqual(self.target.city, "Москва")
        self.assertEqual(merge.filled_fields, ["city"])
        self.assertTrue(
            AuditEvent.objects.filter(organization=self.organization, action="contacts.merged").exists()
        )

    def test_merge_requires_reason(self) -> None:
        with self.assertRaises(ValidationError):
            merge_contacts(
                organization=self.organization,
                target_id=self.target.id,
                source_id=self.source.id,
                reason="  ",
                actor=self.owner,
            )
        self.identity.refresh_from_db()
        self.assertEqual(self.identity.contact_id, self.source.id)

    def test_merge_rejects_already_merged_contact(self) -> None:
        merge_contacts(
            organization=self.organization,
            target_id=self.target.id,
            source_id=self.source.id,
            reason="Совпал телефон",
            actor=self.owner,
        )
        with self.assertRaises(ValidationError):
            merge_contacts(
                organization=self.organization,
                target_id=self.target.id,
                source_id=self.source.id,
                reason="Ещё раз",
                actor=self.owner,
            )

    def test_revert_returns_everything_back(self) -> None:
        merge = merge_contacts(
            organization=self.organization,
            target_id=self.target.id,
            source_id=self.source.id,
            reason="Совпал телефон",
            actor=self.owner,
        )

        revert_merge(
            organization=self.organization,
            merge_id=merge.id,
            reason="Разные люди, ошиблись",
            actor=self.owner,
        )

        self.identity.refresh_from_db()
        self.conversation.refresh_from_db()
        self.source.refresh_from_db()
        self.target.refresh_from_db()
        merge.refresh_from_db()
        self.assertEqual(self.identity.contact_id, self.source.id)
        self.assertEqual(self.conversation.contact_id, self.source.id)
        self.assertIsNone(self.source.merged_into_id)
        self.assertEqual(self.target.city, "")
        self.assertIsNotNone(merge.reverted_at)
        self.assertTrue(
            AuditEvent.objects.filter(organization=self.organization, action="contacts.unmerged").exists()
        )

    def test_revert_twice_is_rejected(self) -> None:
        merge = merge_contacts(
            organization=self.organization,
            target_id=self.target.id,
            source_id=self.source.id,
            reason="Совпал телефон",
            actor=self.owner,
        )
        revert_merge(organization=self.organization, merge_id=merge.id, reason="Ошиблись", actor=self.owner)
        with self.assertRaises(ValidationError):
            revert_merge(organization=self.organization, merge_id=merge.id, reason="Ещё раз", actor=self.owner)

    def test_contact_merged_away_disappears_from_the_list(self) -> None:
        from django.http import QueryDict

        from chatballs.conversations.clients import client_row, clients_queryset

        merge_contacts(
            organization=self.organization,
            target_id=self.target.id,
            source_id=self.source.id,
            reason="Совпал телефон",
            actor=self.owner,
        )
        rows = [client_row(contact) for contact in clients_queryset(self.organization.id, QueryDict())]
        self.assertEqual([row["id"] for row in rows], [self.target.id])


class ContactsMergeApiTests(TestCase):
    """Объединять и разъединять может только владелец (ADR-CHATBALLS-0006)."""

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Ателье", slug="atelie-api")
        self.owner = self._member("owner@atelie.test", EmployeeRole.OWNER)
        self.admin = self._member("admin@atelie.test", EmployeeRole.ADMIN)
        self.channel = Channel.objects.create(organization=self.organization, code="line", name="Линия")
        self.target = Contact.objects.create(organization=self.organization, name="Мария", phone="+79162041187")
        self.source = Contact.objects.create(organization=self.organization, name="Гость")
        Conversation.objects.create(organization=self.organization, channel=self.channel, contact=self.target)
        Conversation.objects.create(organization=self.organization, channel=self.channel, contact=self.source)
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner.user)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin.user)

    def _member(self, email: str, role: str) -> OrganizationMembership:
        user = HumanUser.objects.create_user(email=email, password="Password-123")
        return OrganizationMembership.objects.create(
            user=user, organization=self.organization, role=role, position_title="Specialist"
        )

    def _merge_url(self) -> str:
        return f"/api/v1/conversations/clients/{self.target.id}/merge/"

    def test_owner_merges_and_unmerges(self) -> None:
        merged = self.owner_client.post(
            self._merge_url(),
            {"sourceId": self.source.id, "reason": "Один человек, совпал телефон"},
            format="json",
        )
        self.assertEqual(merged.status_code, 200)
        self.assertEqual(len(merged.json()["client"]["merges"]), 1)
        self.assertEqual(merged.json()["client"]["totalDialogs"], 2)

        merge_id = merged.json()["client"]["merges"][0]["id"]
        reverted = self.owner_client.delete(
            self._merge_url(), {"mergeId": merge_id, "reason": "Разные люди"}, format="json"
        )
        self.assertEqual(reverted.status_code, 200)
        self.assertEqual(reverted.json()["client"]["merges"], [])
        self.assertEqual(reverted.json()["client"]["totalDialogs"], 1)

    def test_card_audit_has_no_raw_codes(self) -> None:
        """В карточке контакта журнал читаемый: ни кода действия, ни enum-а."""

        self.owner_client.post(
            self._merge_url(),
            {"sourceId": self.source.id, "reason": "Один человек, совпал телефон"},
            format="json",
        )
        card = self.owner_client.get(f"/api/v1/conversations/clients/{self.target.id}/")
        self.assertEqual(card.status_code, 200)
        events = card.json()["client"]["audit"]
        self.assertTrue(events)
        merged = next(event for event in events if event["action"] == "Объединение контактов")
        self.assertEqual(merged["object"], f"Контакт · {self.target.id}")
        self.assertEqual(merged["result"], "Выполнено")

    def test_admin_cannot_merge(self) -> None:
        response = self.admin_client.post(
            self._merge_url(),
            {"sourceId": self.source.id, "reason": "Один человек, совпал телефон"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.source.refresh_from_db()
        self.assertIsNone(self.source.merged_into_id)

    def test_reason_is_required_by_the_api(self) -> None:
        response = self.owner_client.post(
            self._merge_url(), {"sourceId": self.source.id, "reason": ""}, format="json"
        )
        self.assertEqual(response.status_code, 400)
