"""Audit periods depend on the organization, including non-HTTP execution."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from django.utils import timezone

from chatballs.identity.audit_queries import _audit_period_start


class AuditPeriodTests(SimpleTestCase):
    def test_organization_midnight_is_independent_of_worker_timezone(self):
        for zone in ("Pacific/Kiritimati", "Pacific/Honolulu"):
            with self.subTest(zone=zone), timezone.override("UTC"):
                local = timezone.localtime(timezone=ZoneInfo(zone))
                start = _audit_period_start("today", zone)
                self.assertEqual(start.date(), local.date())
                self.assertEqual((start.hour, start.minute, start.second), (0, 0, 0))
                self.assertEqual(start.utcoffset(), local.utcoffset())
                self.assertEqual(_audit_period_start("7d", zone).date(), local.date() - timedelta(days=7))
        self.assertIsNone(_audit_period_start("all", "UTC"))
