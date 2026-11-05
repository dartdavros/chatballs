"""Calendar policy boundary checks without network or seeded application data."""

from datetime import UTC, datetime

from django.test import SimpleTestCase

from chatballs.integrations.automation_events.schedule_slots import latest_slot, next_slot, on_day


class ScheduleSlotTests(SimpleTestCase):
    def trigger(self, **changes):
        return {"kind": "schedule", "id": "daily", "timezone": "Europe/Berlin", "frequency": "daily",
            "time": "02:30", "misfire": "once", "ambiguous": "first", "nonexistent": "skip", **changes}

    def test_fold_selects_exactly_one_distinct_slot(self):
        day = datetime(2026, 10, 25).date()
        self.assertEqual(on_day(self.trigger(), day), datetime(2026, 10, 25, 0, 30, tzinfo=UTC))
        self.assertEqual(on_day(self.trigger(ambiguous="second"), day), datetime(2026, 10, 25, 1, 30, tzinfo=UTC))

    def test_gap_skip_or_first_existing_minute(self):
        day = datetime(2026, 3, 29).date()
        self.assertIsNone(on_day(self.trigger(), day))
        self.assertEqual(on_day(self.trigger(nonexistent="next"), day), datetime(2026, 3, 29, 1, tzinfo=UTC))

    def test_latest_missed_slot_and_strict_progression(self):
        after = datetime(2026, 10, 1, tzinfo=UTC)
        now = datetime(2026, 10, 25, 2, tzinfo=UTC)
        slot = latest_slot(self.trigger(), after, now)
        self.assertEqual(slot, datetime(2026, 10, 25, 0, 30, tzinfo=UTC))
        self.assertEqual(next_slot(self.trigger(), slot), datetime(2026, 10, 26, 1, 30, tzinfo=UTC))

    def test_last_day_and_distant_single_date(self):
        trigger = self.trigger(frequency="monthly", dayOfMonth="last", time="09:00")
        self.assertEqual(next_slot(trigger, datetime(2028, 2, 1, tzinfo=UTC)).day, 29)
        trigger = self.trigger(date="2035-01-01", time="09:00")
        self.assertEqual(next_slot(trigger, datetime(2026, 1, 1, tzinfo=UTC)).year, 2035)
