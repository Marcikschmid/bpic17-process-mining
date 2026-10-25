"""Small hand-calculated nets exercise branching, concurrency and nontermination."""

import unittest

from src.runtime import configure_runtime
configure_runtime()
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to
from pm4py.algo.evaluation.simplicity.variants import extended_cardoso as reference_cardoso
from pm4py.algo.evaluation.simplicity.variants import extended_cyclomatic as reference_cyclomatic
from pm4py.objects.petri_net.utils import reachability_graph
import networkx as nx
from src.simplicity import extended_cardoso, model_size, reachability_complexity


def make_net(place_names, routes):
    net = PetriNet("test")
    places = {name: PetriNet.Place(name) for name in place_names}
    net.places.update(places.values())
    for name, inputs, outputs in routes:
        transition = PetriNet.Transition(name, name)
        net.transitions.add(transition)
        for source in inputs:
            add_arc_from_to(places[source], transition, net)
        for target in outputs:
            add_arc_from_to(transition, places[target], net)
    return net, Marking({places[place_names[0]]: 1}), Marking({places[place_names[-1]]: 1})


class SimplicityTests(unittest.TestCase):
    def check_finite(self, model, cardoso, cyclomatic, states, sound=True):
        net, initial, final = model
        own = reachability_complexity(*model)
        self.assertEqual(own["status"], "ok")
        self.assertEqual(own["states_seen"], states)
        self.assertEqual(own["sound"], sound)
        self.assertEqual(extended_cardoso(net), cardoso)
        self.assertEqual(own["value"], cyclomatic)
        self.assertEqual(reference_cardoso.apply(net), cardoso)
        # Independently constructed PM4Py reachability graph, correct TARGET
        # markings. PM4Py 2.7.23.11's metric mistakenly targets edge.name.
        rg = reachability_graph.construct_reachability_graph(net, initial)
        graph = nx.DiGraph()
        graph.add_nodes_from(rg.states)
        graph.add_edges_from((s, edge.to_state) for s in rg.states for edge in s.outgoing)
        self.assertEqual(graph.number_of_edges() - len(graph) +
                         nx.number_strongly_connected_components(graph), cyclomatic)

    def test_sequence(self):
        model = make_net(["i", "m", "o"], [("a", ["i"], ["m"]), ("b", ["m"], ["o"])])
        self.check_finite(model, cardoso=2, cyclomatic=2, states=3)
        self.assertEqual(model_size(model[0]), {"nodes": 5, "arcs": 4})

    def test_distinct_and_duplicate_postsets(self):
        # Two labels with the SAME postset contribute only once to Cardoso,
        # and their parallel state-pair edges count only once in Cyclomatic.
        model = make_net(["i", "o"], [("a", ["i"], ["o"]), ("b", ["i"], ["o"])])
        self.check_finite(model, cardoso=1, cyclomatic=1, states=2)
        branch = make_net(["i", "l", "r", "o"], [
            ("a", ["i"], ["l"]), ("b", ["i"], ["r"]),
            ("c", ["l"], ["o"]), ("d", ["r"], ["o"])])
        self.check_finite(branch, cardoso=4, cyclomatic=4, states=4)

    def test_parallel_branches(self):
        model = make_net(["i", "a", "b", "c", "d", "o"], [
            ("split", ["i"], ["a", "b"]), ("left", ["a"], ["c"]),
            ("right", ["b"], ["d"]), ("join", ["c", "d"], ["o"])])
        self.check_finite(model, cardoso=5, cyclomatic=6, states=6)

    def test_loop_counts_scc(self):
        model = make_net(["i", "m", "o"], [
            ("a", ["i"], ["m"]), ("again", ["m"], ["i"]), ("exit", ["m"], ["o"])])
        self.check_finite(model, cardoso=3, cyclomatic=2, states=3)
        self.assertEqual(reference_cyclomatic.apply(model[0], model[1]), 3)

    def test_deadlock_is_not_sound(self):
        model = make_net(["i", "never", "o"], [("a", ["i", "never"], ["o"])])
        result = reachability_complexity(*model)
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["final_reachable"])
        self.assertFalse(result["sound"])
        self.assertEqual(result["dead_transitions"], ["a"])

    def test_unboundedness_has_actual_pump_witness(self):
        model = make_net(["i", "x", "o"], [("grow", ["i"], ["i", "x"]),
                                              ("exit", ["i"], ["o"])])
        result = reachability_complexity(*model)
        self.assertEqual(result["status"], "unbounded")
        self.assertIsNone(result["value"])
        witness = result["witness"]
        self.assertEqual(witness["pump_sequence"], ["grow"])
        self.assertTrue(all(a <= b for a, b in zip(witness["ancestor_marking"], witness["covering_marking"])))
        self.assertNotEqual(witness["ancestor_marking"], witness["covering_marking"])

    def test_state_limit_is_not_a_complexity_or_unboundedness_result(self):
        model = make_net(["i", "o"], [("a", ["i"], ["o"])])
        result = reachability_complexity(*model, max_states=1)
        self.assertEqual(result["status"], "state_limit")
        self.assertIsNone(result["value"])
        self.assertNotIn("sound", result)


if __name__ == "__main__":
    unittest.main()
