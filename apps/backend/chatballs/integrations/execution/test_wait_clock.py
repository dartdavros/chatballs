"""UTC deadlines remain deterministic across local clock gaps and repeats."""

from datetime import UTC, datetime
from unittest.mock import patch

from django.test import SimpleTestCase

from chatballs.integrations.execution.permissions import ExecutionDenied
from chatballs.integrations.execution.wait_clock import due_at
from chatballs.integrations.scenarios.values import RunValues


class WaitClockTests(SimpleTestCase):
    def deadline(self, now, day, date, time):
        with patch("chatballs.integrations.execution.wait_clock.timezone.now", return_value=now):
            return due_at({"mode": "clock", "day": day, "date": date, "time": time,
                           "timezone": "Europe/Berlin"}, RunValues())

    def test_dst_gap_uses_first_valid_time_and_repeat_uses_future_fold(self):
        self.assertEqual(self.deadline(datetime(2026, 3, 29, 0, tzinfo=UTC), "date", "2026-03-29", "02:30"),
                         datetime(2026, 3, 29, 1, tzinfo=UTC))
        self.assertEqual(self.deadline(datetime(2026, 10, 25, 0, 45, tzinfo=UTC), "date", "2026-10-25", "02:30"),
                         datetime(2026, 10, 25, 1, 30, tzinfo=UTC))

    def test_missing_work_calendar_does_not_invent_weekdays(self):
        with self.assertRaisesMessage(ExecutionDenied, "calendar_unavailable"):
            due_at({"mode": "clock", "day": "work"}, RunValues())
