"""Compare the optimized metric directly against unchanged PM4Py."""
import unittest
import pm4py
from pm4py.objects.log.obj import Event,Trace,EventLog
from pm4py.objects.process_tree.utils.generic import parse
from pm4py.algo.evaluation.precision.variants import align_etconformance
from src.finite_precision import finite_alignment_precision


class FinitePrecisionTests(unittest.TestCase):
    def test_exact_pm4py_scores_with_weights_unfit_prefixes_and_tau_choices(self):
        for expression in ("->('A',+('B','C'))", "X(->('A','B'),->(tau,'A','C'))", "->('A',*('B','C'))"):
            with self.subTest(expression=expression):
                net,im,fm=pm4py.convert_to_petri_net(parse(expression))
                log=EventLog([Trace([Event({'concept:name':a}) for a in sequence]) for sequence in
                    (['A','B','C'],['A','B','C'],['A','C'],['X','A'],['A','B','C','B'])])
                expected=align_etconformance.apply(log,net,im,fm,parameters={'show_progress_bar':False})
                result,_=finite_alignment_precision(log,net,im,fm)
                self.assertAlmostEqual(result['precision'],expected,places=14)


if __name__=='__main__':unittest.main()
