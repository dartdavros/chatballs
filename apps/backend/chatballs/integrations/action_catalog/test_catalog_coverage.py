"""Only executable descriptors may satisfy a product API entry."""

from django.test import SimpleTestCase

from chatballs.i18n.messages import CATALOG
from chatballs.integrations.action_catalog.coverage import inventory, mounted_entries, problems
from chatballs.integrations.action_catalog.registry import native_actions


class NativeCoverageTests(SimpleTestCase):
    def test_every_product_entry_has_an_executable_exact_action(self):
        self.assertEqual(problems(), [])

    def test_inventory_resolves_real_routes_and_method_inheritance(self):
        expected = {(row["route"], row["method"], row["handler"]) for row in inventory()}
        self.assertEqual(mounted_entries(), expected)
        self.assertEqual(len(expected), 160)
        excluded = [row for row in inventory() if row["action"] is None]
        self.assertEqual(len(excluded), 32)
        self.assertTrue(all(row["reason"] for row in excluded))

    def test_registered_domains_cover_their_exact_product_methods(self):
        for prefix in ("messages.post", "messages.request_contact.", "messages.voice.", "messages.attachment.", "messages.transcription.", "messages.email", "contacts.avatar.", "conversations.diagnostic.", "messages.attachment_file.", "messages.audio_file.", "reports.support_csv.", "reports.support_xlsx.", "messages.assistance", "messages.suggestion.", "calls.", "ratings.", "quality.", "reports.overview.", "reports.access.", "reports.support.get", "comments.", "conversations.get", "conversations.detail.", "conversations.counters.", "conversations.directory.", "conversations.activity.", "conversations.participation_journal.", "conversations.visitor_state.", "messages.get", "contacts.from_conversation.", "contacts.get", "contacts.card.", "contacts.merge.", "conversations.priority.", "conversations.note.", "conversations.labels.", "conversations.archive.", "labels.", "notifications.", "participants.", "transfers.", "templates.", "rules.", "conversations.queue_policy.", "conversations.assignment_policy.", "conversations.group.", "conversations.assignee.", "conversations.claim.", "conversations.release.",
                       "conversations.return_queue.", "conversations.close.", "conversations.spam."):
            self.assertEqual(problems(action_prefix=prefix), [])

    def test_executable_actions_have_translated_titles_and_named_inputs(self):
        missing = set()
        def translated(key):
            for language in ("ru", "en"):
                if key not in CATALOG[language]:
                    missing.add(f"{language}:{key}")
                else:
                    self.assertNotIn("??", CATALOG[language][key], f"{language}:{key}")
        def fields(spec):
            for key in (spec.hint_key, spec.placeholder_key, spec.pattern_error_key):
                if key:
                    translated(key)
            for option in spec.options:
                translated(option.label_key)
            for _name, child in spec.properties:
                self.assertTrue(child.title_key)
                translated(child.title_key)
                fields(child)
            if spec.items:
                fields(spec.items)
        for action in native_actions():
            translated(action.operation.title_key)
            self.assertFalse(action.operation.input.open, action.key)
            self.assertTrue(callable(action.execute), action.key)
            fields(action.operation.input)
            fields(action.operation.output)
        self.assertEqual(sorted(missing), [])
