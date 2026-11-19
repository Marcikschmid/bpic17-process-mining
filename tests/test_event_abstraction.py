"""Event abstraction removes only the documented artefacts and keeps every business step and the order."""

import unittest

from src.event_abstraction import (KEPT_EDGE_CASES, MIRROR, SIMULTANEITY_SECONDS, abstract_case, abstract_events,
                                   abstract_labels, is_work_item, work_item_instances)


class EventAbstractionTests(unittest.TestCase):
    def test_completion_rules_drop_mirrors_and_work_item_completions_keep_order(self):
        labels = ["A_Create Application", "A_Submitted", "W_Handle leads", "A_Concept", "A_Accepted",
                  "O_Create Offer", "O_Created", "O_Sent (mail and online)", "W_Complete application", "A_Complete",
                  "A_Validating", "O_Returned", "W_Validate application", "O_Accepted", "A_Pending"]
        kept, applied = abstract_labels(labels, list(range(len(labels))))
        self.assertEqual(kept, ["A_Create Application", "A_Submitted", "A_Concept", "A_Accepted", "O_Create Offer",
                                "O_Sent (mail and online)", "A_Complete", "A_Validating", "O_Returned", "A_Pending"])
        self.assertEqual(applied, {"MIRROR": 2, "WORK_ITEM_COMPLETION": 3})

    def test_collapses_only_simultaneous_direct_repetitions(self):
        labels = ["A_Cancelled", "O_Cancelled", "O_Cancelled", "O_Cancelled"]
        kept, applied = abstract_labels(labels, [0.0, 0.0, 0.5, 0.5 + SIMULTANEITY_SECONDS + 1])
        # The third O_Cancelled is more than 1 s after the kept one: a separate action.
        self.assertEqual(kept, ["A_Cancelled", "O_Cancelled", "O_Cancelled"])
        self.assertEqual(applied, {"SIMULTANEOUS": 1})

    def test_repetition_after_dropped_event_and_non_listed_labels(self):
        # Mirrors in between do not prevent collapsing; non-listed labels are never collapsed.
        kept, _ = abstract_labels(["O_Refused", "O_Created", "O_Refused", "A_Validating", "A_Validating"],
                                  [0.0, 0.1, 0.2, 5.0, 5.0])
        self.assertEqual(kept, ["O_Refused", "A_Validating", "A_Validating"])

    def test_edge_cases_are_kept(self):
        for label in KEPT_EDGE_CASES:
            kept, applied = abstract_labels(["A_Create Application", label], [0.0, 1.0])
            self.assertEqual(kept, ["A_Create Application", label])
            self.assertFalse(applied)
        self.assertFalse(set(KEPT_EDGE_CASES) & set(MIRROR))
        self.assertFalse(any(is_work_item(label) for label in KEPT_EDGE_CASES))

    def test_one_event_per_started_work_item_instance(self):
        events = [{"concept:name": "W_Call after offers", "lifecycle:transition": t}
                  for t in ("schedule", "start", "suspend", "resume", "suspend", "resume", "ate_abort",
                            "schedule", "withdraw",   # never started: no work, no event
                            "start", "complete")]     # second instance
        starts, applied = work_item_instances(events)
        self.assertEqual([next(i for i, x in enumerate(events) if x is e) for e in starts], [1, 9])
        self.assertEqual(applied["WORK_ITEM_LIFECYCLE"], len(events) - 2)

    def test_full_case_merges_work_items_in_original_order(self):
        raw = [("A_Create Application", "complete"), ("W_Complete application", "schedule"),
               ("W_Complete application", "start"), ("A_Concept", "complete"), ("W_Complete application", "suspend"),
               ("O_Create Offer", "complete"), ("O_Created", "complete"), ("W_Complete application", "resume"),
               ("W_Complete application", "complete"), ("W_Assess potential fraud", "start"),
               ("W_Assess potential fraud", "complete"), ("A_Denied", "complete")]
        labels, lifecycles = [a for a, _ in raw], [l for _, l in raw]
        kept, applied = abstract_labels(labels, list(range(len(raw))), lifecycles)
        self.assertEqual(kept, ["A_Create Application", "W_Complete application", "A_Concept", "O_Create Offer",
                                "W_Assess potential fraud", "A_Denied"])
        self.assertEqual(applied["MIRROR"], 1)
        self.assertEqual(applied["WORK_ITEM_COMPLETION"], 2)

    def test_event_objects_and_attributes_are_returned_unchanged(self):
        offer = {"concept:name": "O_Create Offer", "time:timestamp": 3.0, "OfferedAmount": 5000.0,
                 "lifecycle:transition": "complete"}
        events = [{"concept:name": "A_Create Application", "time:timestamp": 1.0, "lifecycle:transition": "complete"},
                  offer, {"concept:name": "O_Created", "time:timestamp": 3.5, "lifecycle:transition": "complete"}]
        kept, _ = abstract_case(events)
        self.assertIs(kept[1], offer)
        self.assertEqual(len(events), 3)

    def test_rejects_missing_timestamp_and_empty_result(self):
        with self.assertRaisesRegex(ValueError, "Missing timestamp"):
            abstract_events([{"concept:name": "O_Refused", "time:timestamp": 0.0}, {"concept:name": "O_Refused"}])
        with self.assertRaisesRegex(ValueError, "removed every event"):
            abstract_labels(["O_Created"], [0.0])
        with self.assertRaisesRegex(ValueError, "removed every event"):
            abstract_labels(["W_Handle leads"], [0.0], ["schedule"])


if __name__ == "__main__":
    unittest.main()
