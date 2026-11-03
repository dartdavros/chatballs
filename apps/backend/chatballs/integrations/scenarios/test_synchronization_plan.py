"""Meaningful mapping/conflict/deletion/echo decisions, without API fixtures."""

from django.test import SimpleTestCase

from chatballs.integrations.scenarios.synchronization_plan import plan


class ExchangePlanTests(SimpleTestCase):
    def pair(self, **changes):
        return {"direction": "both", "sourceOfTruth": "left", "conflict": "source", "deletion": "unlink",
            "fields": [{"left": "status", "right": "STAGE", "direction": "forward", "values": [{"from": "open", "to": "NEW"}]}], **changes}

    def record(self, values, at="2026-11-03T09:00:00+00:00", deleted=False):
        return {"values": values, "modifiedAt": at, "version": "v1", "deleted": deleted}

    def test_unmapped_value_does_not_change_target_and_inverse_is_not_invented(self):
        left, right = self.record({"status": "closed"}), self.record({"STAGE": "NEW"})
        result = plan(self.pair(), left, right)
        self.assertEqual(result["right"], {})
        self.assertEqual(result["left"], {})

    def test_source_mapping_and_echo_do_not_create_a_reverse_change(self):
        left, right = self.record({"status": "open"}), self.record({"STAGE": "OLD"})
        self.assertEqual(plan(self.pair(), left, right)["right"], {"STAGE": "NEW"})
        right = self.record({"STAGE": "NEW"})
        baseline = {"left": left, "right": right}
        result = plan(self.pair(), left, right, baseline=baseline)
        self.assertEqual(result["left"], {})
        self.assertEqual(result["right"], {})

    def test_manual_conflict_requires_each_choice_and_keeps_target_when_selected(self):
        left, right = self.record({"status": "open"}), self.record({"STAGE": "OLD"})
        pair = self.pair(conflict="manual")
        self.assertEqual(len(plan(pair, left, right)["conflicts"]), 1)
        self.assertEqual(plan(pair, left, right, choices={"0": "left"})["right"], {"STAGE": "NEW"})
        self.assertEqual(plan(pair, left, right, choices={"0": "right"})["right"], {})

    def test_latest_and_explicit_reverse_map(self):
        pair = self.pair(sourceOfTruth="latest", conflict="latest", fields=[
            {"left": "status", "right": "STAGE", "direction": "reverse", "values": [{"from": "DONE", "to": "closed"}]}])
        left = self.record({"status": "open"})
        right = self.record({"STAGE": "DONE"}, at="2026-11-03T10:00:00+00:00")
        self.assertEqual(plan(pair, left, right)["left"], {"status": "closed"})

    def test_delete_policies_are_explicit(self):
        left, right = self.record({}, deleted=True), self.record({"STAGE": "NEW"})
        self.assertTrue(plan(self.pair(), left, right)["unlink"])
        self.assertEqual(plan(self.pair(deletion="keep"), left, right)["delete"], "")
        self.assertEqual(plan(self.pair(deletion="propagate"), left, right)["delete"], "right")

    def test_two_directions_share_one_conflict_choice_without_swapping_values(self):
        pair = self.pair(conflict="manual", fields=[
            {"left": "name", "right": "NAME", "direction": "forward"},
            {"left": "name", "right": "NAME", "direction": "reverse"}])
        left, right = self.record({"name": "Local"}), self.record({"NAME": "Remote"})
        self.assertEqual(len(plan(pair, left, right)["conflicts"]), 1)
        result = plan(pair, left, right, choices={"0": "left"})
        self.assertEqual(result["left"], {})
        self.assertEqual(result["right"], {"NAME": "Local"})

    def test_unmapped_status_selection_preserves_target(self):
        pair = self.pair(fields=[{"left": "status", "right": "STAGE", "direction": "forward",
            "values": [{"from": "closed", "to": None}]}])
        left, right = self.record({"status": "closed"}), self.record({"STAGE": "NEW"})
        self.assertEqual(plan(pair, left, right)["right"], {})
