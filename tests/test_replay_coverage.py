"""Exact language membership, including tau closure and parallel ordering."""
import unittest
from pm4py.objects.process_tree.utils.generic import parse
import pm4py
from src.replay_coverage import ExactReplay


class CoverageTests(unittest.TestCase):
    def replay(self, expression):
        return ExactReplay(*pm4py.convert_to_petri_net(parse(expression)))

    def test_sequence_tau_and_case_weights(self):
        replay = self.replay("->('A',tau,'B')")
        result, fits = replay.evaluate([['A','B'],['A','B'],['B','A'],['A']])
        self.assertTrue(replay.sound)
        self.assertEqual(fits, [True,True,False,False])
        self.assertEqual(result['fitting_percentage'], 50)

    def test_parallel_all_interleavings_but_no_duplicate_activity(self):
        replay = self.replay("+('A','B')")
        self.assertTrue(replay.accepts(['A','B']))
        self.assertTrue(replay.accepts(['B','A']))
        self.assertFalse(replay.accepts(['A','A','B']))

    def test_duplicate_labels_require_nondeterministic_marking_sets(self):
        replay = self.replay("X(->('A','B'),->('A','C'))")
        self.assertTrue(replay.accepts(['A','B']))
        self.assertTrue(replay.accepts(['A','C']))
        self.assertFalse(replay.accepts(['A','B','C']))

    def test_loop_arbitrary_finite_repetitions(self):
        replay = self.replay("*('A','B')")
        self.assertTrue(replay.accepts(['A']))
        self.assertTrue(replay.accepts(['A','B','A','B','A']))
        self.assertFalse(replay.accepts(['A','B']))

    def test_state_cap_never_yields_a_coverage_score(self):
        with self.assertRaises(ValueError):
            ExactReplay(*pm4py.convert_to_petri_net(parse("->('A','B')")), max_states=1)

    def test_bpmn_roundtrip_preserves_the_entire_language(self):
        tree = parse("->('A',+('B','C'),*('D','E'))")
        source = ExactReplay(*pm4py.convert_to_petri_net(tree))
        converted = ExactReplay(*pm4py.convert_to_petri_net(pm4py.convert_to_bpmn(tree)))
        self.assertTrue(source.language_equivalent(converted)['equivalent'])
        different = self.replay("->('A','B')")
        verdict = source.language_equivalent(different)
        self.assertFalse(verdict['equivalent'])
        self.assertNotEqual(source.accepts(verdict['counterexample']), different.accepts(verdict['counterexample']))


if __name__ == '__main__': unittest.main()
