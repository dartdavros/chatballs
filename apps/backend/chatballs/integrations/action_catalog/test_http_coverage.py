"""New route prefixes and custom protocol methods cannot evade the inventory."""

from unittest.mock import patch

from django.http import HttpResponse
from django.test import SimpleTestCase
from django.urls import path
from django.views import View

from chatballs.integrations.action_catalog.http_coverage import (
    framework_entries,
    mounted_http_entries,
)


class PlainView(View):
    def get(self, request):
        return HttpResponse()


class CustomView(PlainView):
    def head(self, request):
        return HttpResponse()

    def options(self, request):
        return HttpResponse()


urlpatterns = [path("unanticipated-product/", CustomView.as_view())]


class FullHTTPInventoryTests(SimpleTestCase):
    def test_every_prefix_and_custom_method_requires_its_own_classification(self):
        with patch("chatballs.integrations.action_catalog.http_coverage.SURFACES", {"app": __name__}):
            actual = mounted_http_entries()
        self.assertEqual({entry[2] for entry in actual}, {"GET", "HEAD", "OPTIONS"})
        self.assertTrue(all(entry[1] == "unanticipated-product/" for entry in actual))
        row = {"surface": "app", "route": "unanticipated-product/", "method": "GET",
            "handler": __name__ + ".CustomView"}
        self.assertEqual(list(framework_entries([row])), [])
        row["handler"] = __name__ + ".PlainView"
        self.assertEqual({entry["method"] for entry in framework_entries([row])}, {"HEAD", "OPTIONS"})
