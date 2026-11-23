from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.utils import timezone

from chatballs.identity.instance_settings import InstanceSettings
from chatballs.updates.announcement_state import (
    AnnouncementState,
    parse_schedule,
    save_schedule,
    schedule_snapshot,
)
from chatballs.updates.announcement_subscriber import _configuration, _defer_retry
from chatballs.updates.check_in_state import CheckInState


class AnnouncementScheduleTests(TestCase):
    def test_runtime_role_can_read_and_store_publication_schedule(self):
        with connection.cursor() as cursor:
            for privilege in ("SELECT", "INSERT", "UPDATE"):
                cursor.execute("SELECT has_table_privilege(%s, %s, %s)", [
                    "chatballs_runtime_app", "updates_announcementstate", privilege,
                ])
                self.assertTrue(cursor.fetchone()[0], privilege)

    def setUp(self):
        self.instance = InstanceSettings.load()
        self.revision = self.instance.external_checks_revision
        self.now = timezone.now()
        self.message = {
            "id": 3, "title": "Service", "text": "Scheduled", "link": "",
            "starts_at": self.now.isoformat(), "ends_at": (self.now + timedelta(hours=1)).isoformat(),
        }

    def payload(self, messages=None):
        return {"serverNow": self.now.isoformat(), "announcements": [self.message] if messages is None else messages}

    def test_publication_starting_now_is_saved_independently_of_daily_check_in(self):
        self.assertTrue(save_schedule(self.payload(), self.revision))
        result = schedule_snapshot()
        self.assertEqual(result["announcements"][0]["id"], 3)
        self.assertIn("starts_at", result["announcements"][0])
        self.assertIn("ends_at", result["announcements"][0])
        self.assertIsNone(result["expiresInMs"])
        self.assertLess(abs(result["serverNowMs"] - int(self.now.timestamp() * 1000)), 1000)

    def test_disabled_or_obsolete_attempt_cannot_repopulate_schedule(self):
        save_schedule(self.payload(), self.revision)
        InstanceSettings.objects.filter(pk=1).update(external_checks_enabled=False,
            external_checks_revision=self.revision + 1)
        self.assertFalse(save_schedule(self.payload([]), self.revision))
        self.assertIsNone(schedule_snapshot())
        InstanceSettings.objects.filter(pk=1).update(external_checks_enabled=True)
        self.assertIsNone(schedule_snapshot())

    def test_empty_snapshot_replaces_messages_and_invalid_window_does_not(self):
        save_schedule(self.payload(), self.revision)
        self.message["ends_at"] = self.message["starts_at"]
        with self.assertRaises(ValueError):
            save_schedule(self.payload(), self.revision)
        self.assertEqual(len(AnnouncementState.objects.get().publications), 1)
        save_schedule(self.payload([]), self.revision)
        self.assertEqual(schedule_snapshot()["announcements"], [])

    def test_schedule_requires_absolute_times(self):
        self.message["starts_at"] = "2026-11-22T09:00:00"
        with self.assertRaises(ValueError):
            parse_schedule(self.payload())

    def test_stream_retry_after_survives_executor_change(self):
        self.assertIsNotNone(_configuration())
        _defer_retry(timedelta(hours=2))
        self.assertIsNone(_configuration())
        state = CheckInState.objects.get(pk=1)
        self.assertGreater(state.announcement_retry_at, timezone.now() + timedelta(minutes=119))
        CheckInState.objects.filter(pk=1).update(announcement_retry_at=timezone.now() - timedelta(seconds=1))
        self.assertIsNotNone(_configuration())
