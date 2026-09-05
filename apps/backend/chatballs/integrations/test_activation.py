from django.core.exceptions import ValidationError
from django.test import TestCase

from chatballs.channels.models import Channel
from chatballs.identity.bootstrap import bootstrap_edevs_owner
from chatballs.identity.models import Organization
from chatballs.integrations.models import IntegrationProvider
from chatballs.integrations.serializers import integration_payload
from chatballs.integrations.services import (
    IntegrationInput,
    create_integration,
    update_integration,
)
from chatballs.testing import system_tenant_context


class IntegrationActivationTests(TestCase):
    def setUp(self) -> None:
        bootstrap_edevs_owner(
            email="owner@edevs.tech", password="temporary-password"
        )
        organization = Organization.objects.get(slug="edevs")
        self.context = system_tenant_context(organization)
        self.channel = Channel.objects.create(
            organization=organization,
            code="activation",
            name="Канал подключения",
        )

    def test_activation_round_trip_in_service_and_payload(self) -> None:
        integration = create_integration(
            context=self.context,
            data=IntegrationInput(
                provider=IntegrationProvider.WEB,
                name="Виджет",
                channel_id=self.channel.id,
            ),
        )
        updated = update_integration(
            context=self.context,
            integration=integration,
            data=IntegrationInput(
                provider=integration.provider,
                name=integration.name,
                config=integration.config,
                channel_id=self.channel.id,
                is_active=False,
            ),
        )

        self.assertFalse(updated.is_active)
        self.assertFalse(integration_payload(updated)["isActive"])

    def test_new_binding_to_inactive_channel_is_rejected(self) -> None:
        self.channel.is_active = False
        self.channel.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            create_integration(
                context=self.context,
                data=IntegrationInput(
                    provider=IntegrationProvider.WEB,
                    name="Виджет",
                    channel_id=self.channel.id,
                ),
            )
