"""Protection of prepared conversations registered by the organization demo."""

from django.contrib.contenttypes.models import ContentType

from chatballs.conversations.models import Conversation
from chatballs.identity.demo_models import DemoDatasetStatus, DemoRecord


def inactivity_protection_records(*, organization_id, object_id):
    return DemoRecord.objects.filter(
        organization_id=organization_id,
        dataset__organization_id=organization_id,
        dataset__status__in=(
            DemoDatasetStatus.INSTALLED, DemoDatasetStatus.REINSTALLING, DemoDatasetStatus.REMOVING,
        ),
        content_type=ContentType.objects.get_for_model(Conversation),
        object_id=object_id,
    ).exclude(protect_from_inactivity=False)
