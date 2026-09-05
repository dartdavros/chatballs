from django.test import Client, TestCase


class HealthTests(TestCase):
    def test_live_endpoint(self) -> None:
        response = Client().get("/api/v1/health/live/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["surface"], "app")
