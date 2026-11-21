from datetime import timedelta

import pytest
from django.utils import timezone

from chatballs.identity.instance_settings import InstanceSettings
from chatballs.updates.check_in_client import CheckInResult
from chatballs.updates.check_in_state import CheckInState, finish_attempt, reserve_attempt

OLD_VERSION = "1.23.0"
NEW_VERSION = "1.24.0-rc.1"


@pytest.mark.django_db
@pytest.mark.parametrize("recorded_version", ["", OLD_VERSION])
def test_upgrade_claims_one_check_in_before_daily_deadline(recorded_version):
    previous = reserve_attempt(OLD_VERSION)
    assert finish_attempt(previous, CheckInResult(announcements=[]))
    CheckInState.objects.update(last_attempted_version=recorded_version)
    assert CheckInState.objects.get().next_attempt_at > timezone.now()

    upgrade = reserve_attempt(NEW_VERSION)
    assert upgrade.installation_id == previous.installation_id
    assert CheckInState.objects.get().last_attempted_version == NEW_VERSION
    assert reserve_attempt(NEW_VERSION) is None
    assert finish_attempt(upgrade, CheckInResult(announcements=[]))
    assert reserve_attempt(NEW_VERSION) is None


@pytest.mark.django_db
def test_upgrade_respects_active_claim_and_retry_after_across_policy_changes():
    previous = reserve_attempt(OLD_VERSION)
    assert reserve_attempt(NEW_VERSION) is None

    InstanceSettings.objects.update(external_checks_enabled=False, external_checks_revision=1)
    assert reserve_attempt(NEW_VERSION) is None
    assert finish_attempt(previous, CheckInResult(error="http_429", delay=timedelta(hours=1)))
    InstanceSettings.objects.update(external_checks_enabled=True, external_checks_revision=2)
    assert reserve_attempt(NEW_VERSION) is None

    CheckInState.objects.update(next_attempt_at=timezone.now())
    assert reserve_attempt(NEW_VERSION).installation_id == previous.installation_id
