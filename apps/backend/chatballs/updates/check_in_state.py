"""Installation-wide identity, reservation and service announcement snapshot."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from django.db import models, transaction
from django.db.models.functions import Now

from chatballs.identity.instance_settings import InstanceSettings
from chatballs.updates.check_in_client import (
    DAILY_INTERVAL,
    RETRY_INTERVAL,
    TIMEOUT_SECONDS,
    CheckInResult,
    valid_check_in_version,
)


class CheckInState(models.Model):
    instance = models.OneToOneField(
        "identity.InstanceSettings", primary_key=True, on_delete=models.CASCADE,
    )
    installation_id = models.UUIDField(default=uuid4, editable=False)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    announcement_retry_at = models.DateTimeField(null=True, blank=True)
    attempt_id = models.UUIDField(null=True, blank=True)
    last_attempted_version = models.CharField(max_length=255, blank=True, default="")
    rate_limited = models.BooleanField(default=False)
    announcements = models.JSONField(default=list)
    received_at = models.DateTimeField(null=True, blank=True)
    received_revision = models.PositiveBigIntegerField(null=True, blank=True)
    last_error = models.CharField(max_length=32, blank=True, default="")
    last_result_revision = models.PositiveBigIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return "Backoffice check-in"


@dataclass(frozen=True)
class Attempt:
    installation_id: UUID
    id: UUID
    revision: int


def _lock_instance() -> InstanceSettings:
    instance, _ = InstanceSettings.objects.select_for_update().get_or_create(
        pk=InstanceSettings.SINGLETON_PK,
    )
    return instance


def _states():
    return CheckInState.objects.filter(instance_id=InstanceSettings.SINGLETON_PK)


@transaction.atomic
def reserve_attempt(version: str) -> Attempt | None:
    instance = _lock_instance()
    if not instance.external_checks_enabled:
        return None
    state, _ = CheckInState.objects.get_or_create(instance=instance)
    attempt_id = uuid4()
    due = models.Q(next_attempt_at__isnull=True) | models.Q(next_attempt_at__lte=Now())
    # The deadline doubles as the recovery window if the process dies after claiming.
    reservation = {"attempt_id": attempt_id, "next_attempt_at": Now() + RETRY_INTERVAL}
    if valid_check_in_version(version):
        due |= models.Q(attempt_id__isnull=True, rate_limited=False) & ~models.Q(last_attempted_version=version)
        reservation["last_attempted_version"] = version
    claimed = _states().filter(due).update(**reservation)
    if not claimed:
        return None
    return Attempt(state.installation_id, attempt_id, instance.external_checks_revision)


def still_allowed(attempt: Attempt) -> bool:
    return _states().filter(
        installation_id=attempt.installation_id,
        attempt_id=attempt.id,
        instance__external_checks_enabled=True,
        instance__external_checks_revision=attempt.revision,
        next_attempt_at__gt=Now() + timedelta(seconds=TIMEOUT_SECONDS),
    ).exists()


@transaction.atomic
def finish_attempt(attempt: Attempt, result: CheckInResult) -> bool:
    instance = _lock_instance()
    state = _states().filter(
        installation_id=attempt.installation_id, attempt_id=attempt.id,
        next_attempt_at__gt=Now(),
    ).annotate(db_now=Now()).first()
    if state is None:
        return False
    state.attempt_id = None
    current = instance.external_checks_enabled and instance.external_checks_revision == attempt.revision
    state.rate_limited = result.error == "http_429"
    delay = result.delay if current or state.rate_limited else DAILY_INTERVAL
    state.next_attempt_at = state.db_now + min(delay, datetime.max.replace(tzinfo=UTC) - state.db_now)
    fields = ["attempt_id", "next_attempt_at", "rate_limited"]
    if current:
        state.last_error = result.error
        state.last_result_revision = attempt.revision
        fields += ["last_error", "last_result_revision"]
    if current and result.announcements is not None:
        state.announcements = result.announcements
        state.received_at = state.db_now
        state.received_revision = attempt.revision
        fields += ["announcements", "received_at", "received_revision"]
    state.save(update_fields=fields)
    return True


def announcement_snapshot() -> dict[str, object]:
    """Read the policy and snapshot together and return their current display state."""
    instance = InstanceSettings.objects.filter(pk=InstanceSettings.SINGLETON_PK).select_related(
        "checkinstate",
    ).annotate(db_now=Now()).first()
    enabled = instance is None or instance.external_checks_enabled
    payload: dict[str, object] = {
        "enabled": enabled, "failed": False, "announcements": None, "expiresInMs": None,
    }
    if instance is None or not enabled:
        return payload
    state = getattr(instance, "checkinstate", None)
    if state is None:
        return payload
    revision = instance.external_checks_revision
    payload["failed"] = state.last_result_revision == revision and bool(state.last_error)
    if state.received_at is not None and state.received_revision == revision:
        remaining = state.received_at + DAILY_INTERVAL - instance.db_now
        milliseconds = remaining // timedelta(milliseconds=1)
        if milliseconds > 0:
            payload.update(announcements=state.announcements, expiresInMs=milliseconds)
    return payload


@transaction.atomic
def reset_for_independent_copy() -> None:
    instance = _lock_instance()
    instance.external_checks_enabled = False
    instance.external_checks_revision += 1
    instance.save(update_fields=["external_checks_enabled", "external_checks_revision", "updated_at"])
    _states().delete()
    CheckInState.objects.create(instance=instance)
