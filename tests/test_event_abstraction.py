"""Event abstraction removes only the documented artefacts and keeps edge cases and order."""

import unittest

from src.event_abstraction import (KEPT_EDGE_CASES, MIRROR, SIMULTANEITY_SECONDS, WORK_ITEM, abstract_events,
                                   abstract_labels)


class EventAbstractionTests(unittest.TestCase):
    def test_drops_mirrors_and_work_items_keeps_order(self):
        labels = ["A_Create Application", "A_Submitted", "W_Handle leads", "A_Concept", "A_Accepted",
                  "O_Create Offer", "O_Created", "O_Sent (mail and online)", "W_Complete application", "A_Complete",
                  "A_Validating", "O_Returned", "W_Validate application", "O_Accepted", "A_Pending"]
        kept, applied = abstract_labels(labels, list(range(len(labels))))
        self.assertEqual(kept, ["A_Create Application", "A_Submitted", "A_Concept", "A_Accepted", "O_Create Offer",
                                "O_Sent (mail and online)", "A_Complete", "A_Validating", "O_Returned", "A_Pending"])
        self.assertEqual(applied, {"MIRROR": 2, "WORK_ITEM": 3})

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
        self.assertFalse(set(KEPT_EDGE_CASES) & set(MIRROR + WORK_ITEM))

    def test_event_objects_and_attributes_are_returned_unchanged(self):
        offer = {"concept:name": "O_Create Offer", "time:timestamp": 3.0, "OfferedAmount": 5000.0}
        events = [{"concept:name": "A_Create Application", "time:timestamp": 1.0}, offer,
                  {"concept:name": "O_Created", "time:timestamp": 3.5}]
        kept, _ = abstract_events(events)
        self.assertIs(kept[1], offer)
        self.assertEqual(len(events), 3)

    def test_rejects_missing_timestamp_and_empty_result(self):
        with self.assertRaisesRegex(ValueError, "Missing timestamp"):
            abstract_events([{"concept:name": "O_Refused", "time:timestamp": 0.0}, {"concept:name": "O_Refused"}])
        with self.assertRaisesRegex(ValueError, "removed every event"):
            abstract_labels(["O_Created"], [0.0])


if __name__ == "__main__":
    unittest.main()
