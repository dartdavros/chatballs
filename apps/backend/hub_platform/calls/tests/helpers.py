from django.test import TestCase

from hub_platform.channels.models import Channel
from hub_platform.conversations.models import ConnectionIdentity, Contact, Conversation
from hub_platform.identity.bootstrap import bootstrap_edevs_owner
from hub_platform.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
)
from hub_platform.integrations.models import Integration, IntegrationKind, IntegrationProvider
from hub_platform.tenancy.context import TenantActorKind, TenantContext


def create_call_request(*, conversation_id: int, initiator: HumanUser):
    """Keep historical call fixtures concise while exercising explicit tenancy."""

    conversation = Conversation.objects.only("organization_id").get(id=conversation_id)
    membership = OrganizationMembership.objects.select_related("organization", "user").get(
        organization_id=conversation.organization_id,
        user=initiator,
    )
    from hub_platform.calls.services import create_call_request as create_with_context

    return create_with_context(
        context=TenantContext.for_membership(membership),
        conversation_id=conversation_id,
    )


def expire_stale_calls(organization: Organization) -> int:
    """Run one organization's maintenance pass in legacy call fixtures."""

    from hub_platform.calls.maintenance import expire_stale_calls as expire_with_context

    return expire_with_context(
        TenantContext.for_resource(organization, actor_kind=TenantActorKind.SYSTEM)
    )


class CallDomainMixin:
    """Общий домен тестов звонков. Отдельно от TestCase, чтобы signaling-тесты
    могли использовать TransactionTestCase (consumer работает в потоках)."""

    def setUp(self) -> None:
        bootstrap_edevs_owner(email="owner@edevs.tech", password="temporary-password")
        self.organization = Organization.objects.get(slug="edevs")
        self.operators_group = self.organization.employee_groups.get(name="Операторы")
        self.support_group = self.organization.employee_groups.get(name="Поддержка")
        self.owner = HumanUser.objects.get(email="owner@edevs.tech")
        self.operator = HumanUser.objects.get(email="a.kotova@edevs.tech")
        self.channel = Channel.objects.create(
            organization=self.organization,
            group=self.operators_group,
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
            group=self.operators_group,
            connection=self.connection,
            contact=self.contact,
        )

    def create_support_operator(self) -> HumanUser:
        user = HumanUser.objects.create_user(
            email="support-operator@edevs.tech",
            password="support-password",
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=self.organization,
            role=EmployeeRole.EMPLOYEE,
            position_title="Оператор поддержки",
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
            group=self.operators_group,
            connection=self.connection,
            contact=contact,
        )


class CallTestCase(CallDomainMixin, TestCase):
    pass
