"""Global profile functionality must never be disguised as a login protocol."""

import json
from pathlib import Path

from django.test import SimpleTestCase

from chatballs.identity.auth_urls import urlpatterns


class AuthBoundaryTests(SimpleTestCase):
    def test_actual_auth_routes_preserve_product_and_credential_boundaries(self):
        rows = json.loads(Path(__file__).with_name("auth_boundary_inventory.json").read_text(encoding="utf-8"))
        expected = {(row["route"], row["method"], row["handler"]) for row in rows}
        actual = set()
        for pattern in urlpatterns:
            view = pattern.callback.cls
            for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                if hasattr(view, method.lower()):
                    actual.add(("api/v1/auth/" + str(pattern.pattern), method, view.__module__ + "." + view.__name__))
        self.assertEqual(actual, expected)
        self.assertEqual(len(expected), len(rows))
        for row in rows:
            self.assertTrue(row["reason"])
            self.assertTrue(row["evidence"])
            self.assertIn(row["classification"], {"global_product", "credential_protocol"})
            if row["classification"] == "global_product":
                self.assertEqual(row["ownerTask"], "T-176")
        product_routes = {row["route"] for row in rows if row["classification"] == "global_product"}
        for name in ("update", "appearance", "language", "avatar", "sessions", "sessions/revoke-other"):
            self.assertIn(f"api/v1/auth/profile/{name}/", product_routes)
