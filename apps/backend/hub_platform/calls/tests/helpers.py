from django.test import TestCase

from hub_platform.channels.models import Channel
from hub_platform.conversations.models import ConnectionIdentity, Contact, Conversation
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import EmployeeProfile, EmployeeRole, HumanUser, Organization
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationProvider


class CallDomainMixin:
    """Общий домен тестов звонков. Отдельно от TestCase, чтобы signaling-тесты
    могли использовать TransactionTestCase (consumer работает в потоках)."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.sales_department = self.organization.departments.get(code="sales")
        self.support_department = self.organization.departments.get(code="support")
        self.owner = HumanUser.objects.get(email="owner@edevs.tech")
        self.operator = HumanUser.objects.get(email="a.kotova@edevs.tech")
        self.channel = Channel.objects.create(
            organization=self.organization,
            department=self.sales_department,
            code="call-sales",
            name="Звонки — продажи",
        )
        self.connection = Integration.objects.create(
            organization=self.organization,
            kind=IntegrationKind.MESSENGER,
            provider=IntegrationProvider.WEB,
            name="call-web",
            channel=self.channel,
        )
        self.contact = Contact.objects.create(organization=self.organization, name="Анна")
        self.identity = ConnectionIdentity.objects.create(
            contact=self.contact,
            connection=self.connection,
            external_user_id="customer-1",
            display_name="Анна",
        )
        self.conversation = Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            connection=self.connection,
            contact=self.contact,
        )

    def create_support_operator(self) -> HumanUser:
        user = HumanUser.objects.create_user(
            email="support-operator@edevs.tech",
            password="support-password",
        )
        EmployeeProfile.objects.create(
            user=user,
            organization=self.organization,
            role=EmployeeRole.OPERATOR,
            department=self.support_department,
        )
        return user

    def create_second_conversation(self) -> Conversation:
        contact = Contact.objects.create(organization=self.organization, name="Мария")
        ConnectionIdentity.objects.create(
            contact=contact,
            connection=self.connection,
            external_user_id="customer-2",
            display_name="Мария",
        )
        return Conversation.objects.create(
            organization=self.organization,
            channel=self.channel,
            connection=self.connection,
            contact=contact,
        )


class CallTestCase(CallDomainMixin, TestCase):
    pass
