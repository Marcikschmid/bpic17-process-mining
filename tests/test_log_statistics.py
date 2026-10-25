"""Check definitions that materially affect Assignment 3.2 statistics."""

import math
import unittest
from datetime import datetime
from pm4py.objects.log.obj import Event, EventLog, Trace
from src.log_statistics import compute_statistics


def event(label, timestamp, **attributes):
    return Event({"concept:name": label, "time:timestamp": datetime.fromisoformat(timestamp), **attributes})


def trace(name, events, **attributes):
    return Trace(events, attributes={"concept:name": name, **attributes})


class LogStatisticsTests(unittest.TestCase):
    def test_original_order_variants_and_max_min_durations(self):
        log = EventLog([
            trace("a", [event("A", "2020-01-01T00:01:00+00:00"), event("B", "2020-01-01T00:00:00+00:00")]),
            trace("b", [event("A", "2020-01-01T01:00:00+01:00"), event("B", "2020-01-01T00:03:00+00:00")]),
            trace("c", [event("B", "2020-01-02T00:00:00+00:00")])])
        summary, cases, variants = compute_statistics(log)
        self.assertEqual(summary["variants"], 2)
        self.assertEqual(summary["events"], 5)
        self.assertEqual(variants[0]["cases"], 2)
        self.assertEqual(cases[0]["duration_seconds"], 60)
        self.assertEqual(cases[1]["duration_seconds"], 180)
        self.assertEqual(summary["case_duration"]["seconds"]["mean"], 80)
        self.assertAlmostEqual(summary["case_duration"]["seconds"]["std_population"], math.sqrt(5600))
        self.assertAlmostEqual(summary["case_duration"]["minutes"]["std_population"], math.sqrt(5600)/60)
        self.assertEqual(summary["quality_checks"]["cases_with_descending_timestamps"], 1)
        self.assertEqual(summary["case_length"]["mean"], 5/3)
        self.assertAlmostEqual(summary["case_length"]["std_population"], math.sqrt(2/9))

    def test_attribute_unions_missingness_and_semantic_types(self):
        log = EventLog([trace("a", [
            event("A", "2020-01-01T00:00:00+00:00", Accepted=True, NumberOfTerms=1, EventID="e1"),
            event("A", "2020-01-01T00:01:00+00:00", Accepted=False, CreditScore=None, EventID="e2")], LoanGoal="Car")])
        summary, _, _ = compute_statistics(log)
        self.assertEqual(summary["case_attribute_count"], 2)
        self.assertEqual(summary["event_attribute_count"], 6)
        self.assertEqual(summary["event_attributes"]["NumberOfTerms"]["classification"], "numeric")
        self.assertEqual(summary["event_attributes"]["Accepted"]["distinct_non_null"], 2)
        self.assertEqual(summary["event_attributes"]["CreditScore"]["missing"], 2)
        self.assertEqual(summary["event_attributes"]["NumberOfTerms"]["missing"], 1)
        self.assertIn("EventID", summary["categorical_event_attributes"])
        self.assertNotIn("EventID", summary["categorical_event_attributes_excluding_event_offer_ids"])

    def test_lifecycle_is_a_separate_variant_definition(self):
        log = EventLog([trace(str(i), [event("A", "2020-01-01T00:00:00+00:00", **{"lifecycle:transition": state})])
                       for i, state in enumerate(("start", "complete"))])
        summary, _, _ = compute_statistics(log)
        self.assertEqual(summary["variants"], 1)
        self.assertEqual(summary["activity_lifecycle_variants"], 2)

    def test_rejects_undefined_durations_and_invalid_identifiers(self):
        good = event("A", "2020-01-01T00:00:00+00:00")
        for log in (EventLog(), EventLog([trace("a", [])]),
                    EventLog([trace("a", [good]), trace("a", [good])]),
                    EventLog([trace("a", [event("A", "2020-01-01T00:00:00")])])):
            with self.assertRaises(ValueError):
                compute_statistics(log)


if __name__ == "__main__":
    unittest.main()
