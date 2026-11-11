"""Category metadata survives edits/copies without changing scenario authority."""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from chatballs.integrations.scenarios.categories import category_path
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.test_api import ScenarioAPICase


class CategoryValidationTests(SimpleTestCase):
    def test_empty_path_and_trimmed_nested_names(self):
        self.assertEqual(category_path([]), [])
        self.assertEqual(category_path([" Продажи ", " Лиды "]), ["Продажи", "Лиды"])

    def test_rejects_ambiguous_or_unbounded_metadata(self):
        for value in (None, "Sales", {}, [None], [1], [""], ["  "], ["A/B"],
                      ["line\nfeed"], ["x" * 81], ["a", "b", "c", "d"]):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                category_path(value)


class ScenarioCategoryAPITests(ScenarioAPICase):
    def create_categorized(self):
        response = self.client.post(self.url(), {
            "name": "Categorized", "definition": empty_definition(),
            "categoryPath": [" Sales ", " Leads "],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["scenario"]

    def test_round_trip_copy_and_legacy_update_preserve_categories(self):
        row = self.create_categorized()
        expected = ["Sales", "Leads"]
        self.assertEqual(row["categoryPath"], expected)
        self.assertEqual(self.client.get(self.url()).json()["items"][0]["categoryPath"], expected)
        response = self.client.put(self.url(f"{row['id']}/"), {
            "name": "Legacy edit", "definition": row["definition"], "revision": row["revision"],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scenario"]["categoryPath"], expected)
        copied = self.client.post(self.url(f"{row['id']}/copy/"), {"name": "Copy"}, format="json")
        self.assertEqual(copied.status_code, 201, copied.content)
        self.assertEqual(copied.json()["scenario"]["categoryPath"], expected)
        self.assertEqual(copied.json()["scenario"]["definition"]["access"]["staff"], [])

    def test_explicit_empty_path_clears_category(self):
        row = self.create_categorized()
        response = self.client.put(self.url(f"{row['id']}/"), {
            "name": row["name"], "definition": row["definition"],
            "revision": row["revision"], "categoryPath": [],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["scenario"]["categoryPath"], [])

    def test_invalid_path_is_rejected_at_the_definition_boundary(self):
        for value in (None, "Sales", [""], ["A/B"], ["a", "b", "c", "d"]):
            with self.subTest(value=value):
                response = self.client.post(self.url(), {
                    "name": "Invalid", "definition": empty_definition(), "categoryPath": value,
                }, format="json")
                self.assertEqual(response.status_code, 400, response.content)

    def test_existing_definition_defaults_to_uncategorized(self):
        self.assertEqual(self.create()["categoryPath"], [])
