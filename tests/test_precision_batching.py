"""Batched Align-ET must equal the unmodified PM4Py implementation."""

import unittest

from src.quality import alignment_precision_batched
from pm4py.algo.evaluation.precision.variants import align_etconformance
from pm4py.objects.log.obj import Event, EventLog, Trace
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to


def fixture(sequences):
    net = PetriNet("choice")
    places = {name: PetriNet.Place(name) for name in ("i", "m", "q", "o")}
    net.places.update(places.values())
    for label, source, target in (("A", "i", "m"), ("B", "m", "q"),
                                  ("C", "m", "q"), ("D", "m", "q"), ("Z", "q", "o")):
        transition = PetriNet.Transition(label, label)
        net.transitions.add(transition)
        add_arc_from_to(places[source], transition, net)
        add_arc_from_to(transition, places[target], net)
    log = EventLog([Trace([Event({"concept:name": a}) for a in sequence],
                         attributes={"concept:name": str(i)}) for i, sequence in enumerate(sequences)])
    return log, net, Marking({places["i"]: 1}), Marking({places["o"]: 1})


class BatchedPrecisionTests(unittest.TestCase):
    def test_exact_global_weights_with_multiple_prefix_batches(self):
        args = fixture(["ABZ", "ACZ", "ABZ"])
        params = {"show_progress_bar": False, "multiprocessing": False}
        original = align_etconformance.apply(*args, parameters=dict(params))
        self.assertAlmostEqual(original, .8)
        for size in (1, 2, 128):
            with self.subTest(batch_size=size):
                result = alignment_precision_batched(*args, parameters=params, batch_size=size)
                self.assertEqual(result["prefixes"], 3)
                self.assertAlmostEqual(result["precision"], original)
                self.assertEqual(result["weighted_unfit_prefixes"], 0)

    def test_nonfitting_prefixes_follow_original_pm4py_semantics(self):
        args = fixture(["ABZ", "AXZ", "ACZ"])
        params = {"show_progress_bar": False, "multiprocessing": False}
        original = align_etconformance.apply(*args, parameters=dict(params))
        result = alignment_precision_batched(*args, parameters=params, batch_size=1)
        self.assertAlmostEqual(result["precision"], original)


if __name__ == "__main__":
    unittest.main()
