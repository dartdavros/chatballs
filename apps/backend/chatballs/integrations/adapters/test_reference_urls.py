"""Linked-record navigation cannot expose the saved webhook secret."""

from django.test import SimpleTestCase

from chatballs.integrations.adapters.bitrix24.references import references


class ReferenceURLTests(SimpleTestCase):
    def test_navigation_uses_portal_origin_and_numeric_record_only(self):
        ref = references("contact")
        self.assertEqual(ref.record_url({"url": "https://portal.example/rest/7/private-secret/"}, "42"),
            "https://portal.example/crm/contact/details/42/")
        self.assertEqual(ref.record_url({"url": "https://portal.example/rest/7/private-secret/"}, "../secret"), "")
        self.assertEqual(ref.record_url({"url": "http://portal.example/rest/7/private-secret/"}, "42"), "")
