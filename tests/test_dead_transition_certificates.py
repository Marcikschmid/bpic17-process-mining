"""Distinguish impossible XOR joins from reachable parallel joins."""

import unittest
from src.runtime import configure_runtime
configure_runtime()
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to
from src.validation import dead_transition_certificates, verify_dead_transition_certificate


def fixture(parallel=False):
    net = PetriNet("join")
    places = {n: PetriNet.Place(n) for n in ("i", "q", "r", "o")}
    net.places.update(places.values())
    routes = [("split", ["i"], ["q", "r"])] if parallel else [
        ("left", ["i"], ["q"]), ("right", ["i"], ["r"])]
    routes.append(("join", ["q", "r"], ["o"]))
    for name, incoming, outgoing in routes:
        t = PetriNet.Transition(name, name)
        net.transitions.add(t)
        for p in incoming:
            add_arc_from_to(places[p], t, net)
        for p in outgoing:
            add_arc_from_to(t, places[p], net)
    return net, Marking({places["i"]: 1})


class DeadTransitionTests(unittest.TestCase):
    def test_exclusive_tokens_cannot_enable_and_join(self):
        net, initial = fixture()
        proofs = dead_transition_certificates(net, initial)
        self.assertEqual(set(proofs), {"join"})
        self.assertTrue(verify_dead_transition_certificate(net, initial, "join", proofs["join"]))

    def test_parallel_join_must_not_be_classified_as_dead(self):
        net, initial = fixture(parallel=True)
        self.assertEqual(dead_transition_certificates(net, initial), {})
        # The same weights fail the split's nonincrease inequality here.
        self.assertFalse(verify_dead_transition_certificate(net, initial, "join", {"i": "1", "q": "1", "r": "1"}))

    def test_missing_or_negative_weights_do_not_form_a_proof(self):
        net, initial = fixture()
        self.assertFalse(verify_dead_transition_certificate(net, initial, "join", {}))
        self.assertFalse(verify_dead_transition_certificate(net, initial, "join", {"q": "-1"}))


if __name__ == "__main__":
    unittest.main()
