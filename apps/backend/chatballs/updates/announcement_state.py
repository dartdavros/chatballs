"""Publication schedules are independent of the daily installation check-in."""

from django.db import models, transaction
from django.db.models.functions import Now
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from chatballs.identity.instance_settings import InstanceSettings
from chatballs.realtime import publish
from chatballs.updates.check_in_client import parse_announcements

ANNOUNCEMENT_GROUP = "installation.announcements"


class AnnouncementState(models.Model):
    instance = models.OneToOneField("identity.InstanceSettings", primary_key=True, on_delete=models.CASCADE)
    revision = models.PositiveBigIntegerField()
    publications = models.JSONField(default=list)
    clock_offset_ms = models.BigIntegerField(default=0)

    def __str__(self):
        return "Backoffice publication schedule"


def parse_schedule(payload):
    publications = parse_announcements(payload)
    now = parse_datetime(payload.get("serverNow", ""))
    if now is None or timezone.is_naive(now):
        raise ValueError("Invalid publication clock")
    for item, original in zip(publications, payload["announcements"], strict=True):
        start = parse_datetime(original.get("starts_at", ""))
        end = parse_datetime(original.get("ends_at", ""))
        if start is None or end is None or timezone.is_naive(start) or timezone.is_naive(end) or start >= end:
            raise ValueError("Invalid publication window")
        item.update(starts_at=start.isoformat(), ends_at=end.isoformat())
    return publications, now


@transaction.atomic
def save_schedule(payload, revision):
    publications, server_now = parse_schedule(payload)
    instance = InstanceSettings.objects.select_for_update().annotate(db_now=Now()).get(pk=1)
    if not instance.external_checks_enabled or instance.external_checks_revision != revision:
        return False
    AnnouncementState.objects.update_or_create(instance=instance, defaults={
        "revision": revision, "publications": publications,
        "clock_offset_ms": int((server_now - instance.db_now).total_seconds() * 1000),
    })
    transaction.on_commit(lambda: publish(ANNOUNCEMENT_GROUP, {"type": "announcements.changed"}))
    return True


def schedule_snapshot():
    state = AnnouncementState.objects.select_related("instance").annotate(db_now=Now()).filter(pk=1).first()
    if state is None or not state.instance.external_checks_enabled:
        return None
    if state.revision != state.instance.external_checks_revision:
        return None
    return {
        "enabled": True, "failed": False, "announcements": state.publications,
        "serverNowMs": int(state.db_now.timestamp() * 1000) + state.clock_offset_ms,
        "expiresInMs": None,
    }
