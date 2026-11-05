from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import patch

from django.test import SimpleTestCase

from chatballs.integrations.adapters.http import _retry_after
from chatballs.integrations.execution.recovery import backoff


class RetryAfterTests(SimpleTestCase):
    def test_http_date_and_multi_day_delay_are_respected(self):
        now = datetime(2026, 10, 30, 12, tzinfo=UTC)
        with patch("chatballs.integrations.adapters.http.datetime") as clock:
            clock.now.return_value = now
            value = _retry_after(format_datetime(now + timedelta(days=2), usegmt=True))
        self.assertEqual(value, 172800)
        self.assertGreaterEqual(backoff(2, value), value)
        self.assertEqual(_retry_after("120"), 120)
        self.assertIsNone(_retry_after("invalid"))
