"""Guard the common discovery input against silent case loss or reordering."""

import unittest
from datetime import datetime, timezone

from src.discovery import completion_projection
from pm4py.objects.log.obj import Event, EventLog, Trace


def event(activity, lifecycle, day):
    return Event({"concept:name": activity, "lifecycle:transition": lifecycle,
                  "time:timestamp": datetime(2017, 1, day, tzinfo=timezone.utc)})


class CompletionProjectionTests(unittest.TestCase):
    def test_keeps_cases_attributes_and_xes_order_without_mutating_raw_log(self):
        # Deliberately non-chronological: do not silently sort timestamps.
        first = Trace([event("B", "complete", 3), event("A", "start", 1),
                       event("A", "complete", 2)],
                      attributes={"concept:name": "case1", "RequestedAmount": 1000})
        second = Trace([event("C", "complete", 4)], attributes={"concept:name": "case2"})
        raw = EventLog([first, second])
        original_events = [[dict(e) for e in t] for t in raw]
        projected, summary = completion_projection(raw)
        self.assertEqual([t.attributes for t in projected], [t.attributes for t in raw])
        self.assertEqual([e["concept:name"] for e in projected[0]], ["B", "A"])
        self.assertEqual([len(t) for t in raw], [3, 1])
        self.assertEqual([[dict(e) for e in t] for t in raw], original_events)
        projected[0][0]["concept:name"] = "Changed only in projection"
        self.assertEqual(raw[0][0]["concept:name"], "B")
        self.assertEqual(summary["discovery_events"], 3)
        self.assertEqual(summary["excluded_events"], 1)

    def test_rejects_case_without_completion_instead_of_silent_case_removal(self):
        raw = EventLog([Trace([event("A", "start", 1)], attributes={"concept:name": "case1"})])
        with self.assertRaisesRegex(ValueError, "removed/reordered cases"):
            completion_projection(raw)

    def test_rejects_missing_lifecycle_and_duplicate_case_id(self):
        incomplete = event("A", "complete", 1)
        del incomplete["lifecycle:transition"]
        with self.assertRaisesRegex(ValueError, "Missing lifecycle"):
            completion_projection(EventLog([Trace([incomplete], attributes={"concept:name": "case1"})]))
        trace = Trace([event("A", "complete", 1)], attributes={"concept:name": "case1"})
        with self.assertRaisesRegex(ValueError, "unique"):
            completion_projection(EventLog([trace, trace]))


if __name__ == "__main__":
    unittest.main()
